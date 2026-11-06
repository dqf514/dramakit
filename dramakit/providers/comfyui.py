"""ComfyUI client — drives a local OR remote ComfyUI server.

Remote-ready:
  * auth on every HTTP call and the progress WebSocket (Basic / Bearer / custom headers)
  * optional TLS verification off for self-signed internal certs
  * retries on transient network errors
  * progress via WebSocket, with automatic fallback to polling /history when a
    reverse proxy blocks the WS upgrade

Workflow templates are ComfyUI "API format" JSON exports. We inject runtime
values (prompt / negative / seed / size / image) into specific node ids listed
in config.comfyui.t2i_nodes / i2v_nodes. Export your workflow with
"Save (API Format)" and drop it in config/comfyui/.

If your video server exposes a plain REST API instead of ComfyUI, implement
BaseImageVideo and return it from providers/__init__.build_visual().
"""
from __future__ import annotations

import asyncio
import base64
import copy
import json
import logging
import random
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import httpx

from ..config import ComfyUIConfig
from .base import BaseImageVideo
from .workflow_map import infer_workflow, score_workflow

log = logging.getLogger("dramakit.comfyui")


def _ref_slots(node: dict, key: str) -> tuple[dict, str]:
    """Read one reference slot group, whichever shape the workflow wrote.

    A workflow reaches the API in two shapes for the same thing: a nested
    map under the key - ``{"ref_images": {"ref_image_0": [...]}}`` - or one
    flat key per slot - ``{"ref_images.ref_image_0": [...]}``. ComfyUI takes
    both. A reader that only knows one shape gets an empty dict from the
    other, and an empty dict here means the pictures are never uploaded:
    the loaders keep the file's own placeholders, and the model renders a
    character that is not in the script.

    Returns the slots and the shape they came in, so the caller can put
    them back the way it found them.
    """
    inputs = node.get("inputs") or {}
    nested = inputs.get(key)
    if isinstance(nested, dict):
        return dict(nested), "nested"
    prefix = key + "."
    flat = {k[len(prefix):]: v for k, v in inputs.items()
            if k.startswith(prefix) and isinstance(v, list)}
    return flat, "flat"


def _put_ref_slots(node: dict, key: str, slots: dict, shape: str) -> None:
    """Write a slot group back in the shape it was read in."""
    inputs = node.setdefault("inputs", {})
    if shape == "nested":
        inputs[key] = slots
        return
    for name in [k for k in inputs if k.startswith(key + ".")]:
        del inputs[name]
    for name, link in slots.items():
        inputs[f"{key}.{name}"] = link


def sage_node(graph: dict) -> str:
    """The attention patch in this graph, or "" when there is none.

    SageAttention is the card's own accelerator for H3 and the reason this
    workflow exists rather than a plainer one: it takes roughly a third off
    the render. A graph without it still renders, at full price, and
    nothing says so - the loss is invisible in the log and only shows up as
    a video that took longer than it should. So the presence is named at
    submit time and checked when the workflow is validated, which is where
    a swapped or missing file gets caught.
    """
    for nid, node in graph.items():
        if isinstance(node, dict) and "SageAttention" in str(node.get("class_type", "")):
            return str(nid)
    return ""


def bypassable(node: dict) -> bool:
    """True when a node can be taken out and its users pointed past it.

    A plugin a card does not have should not stop the card from working.
    The usual case is the attention patch: the card runs the model
    perfectly well without it, only slower. Such a node is a patch - it
    takes one thing in and gives the same kind of thing out - so removing
    it and connecting its users to what fed it leaves a graph that still
    means what it meant.
    """
    inputs = node.get("inputs") or {}
    links = [k for k, v in inputs.items()
             if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str)]
    return links == ["model"]


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient(BaseImageVideo):
    def __init__(self, cfg: ComfyUIConfig, root: Optional[Path] = None):
        self.cfg = cfg
        self.root = Path(root) if root else Path(".")
        self.base = cfg.base_url.rstrip("/")
        # this node's own weights (the loader nodes of the workflow)
        self.graph_overrides: dict = getattr(cfg, "graph_overrides", None) or {}
        # unique-ish client id so multiple machines don't cross-talk on the WS
        self.client_id = f"{cfg.client_id}-{random.randint(1000, 9999)}"
        self._infer_cache: dict[str, tuple[float, dict]] = {}

    # ---------------------------------------------------------------- auth
    def _auth_headers(self) -> dict:
        h: dict[str, str] = {}
        mode = self.cfg.auth
        if mode == "basic" and self.cfg.auth_username:
            token = base64.b64encode(
                f"{self.cfg.auth_username}:{self.cfg.auth_password}".encode()).decode()
            h["Authorization"] = f"Basic {token}"
        elif mode == "token" and self.cfg.auth_token:
            h["Authorization"] = f"Bearer {self.cfg.auth_token}"
        # custom/extra headers always merged (auth == "header" relies on this)
        h.update(self.cfg.extra_headers or {})
        return h

    def _client(self, timeout: Optional[float] = None) -> httpx.Client:
        return httpx.Client(
            timeout=timeout if timeout is not None else self.cfg.request_timeout,
            headers=self._auth_headers(),
            verify=self.cfg.verify_tls,
            trust_env=self.cfg.use_proxy,
        )

    # ------------------------------------------------------------- HTTP core
    def _request(self, method: str, url: str, *, retry: bool = True, **kw) -> httpx.Response:
        attempts = (self.cfg.max_retries + 1) if retry else 1
        last: Optional[Exception] = None
        for i in range(attempts):
            try:
                with self._client(kw.pop("timeout", None)) as c:
                    r = c.request(method, url, **kw)
                if r.status_code in (502, 503, 504) and i < attempts - 1:
                    last = ComfyUIError(f"HTTP {r.status_code}")
                    time.sleep(1.5 * (i + 1))
                    continue
                return r
            except httpx.TransportError as e:
                last = e
                if i < attempts - 1:
                    time.sleep(1.5 * (i + 1))
                    continue
        raise ComfyUIError(f"ComfyUI 请求失败 {method} {url}: {last}")

    def _get(self, path: str, **kw) -> httpx.Response:
        return self._request("GET", f"{self.base}{path}", **kw)

    def _post(self, path: str, **kw) -> httpx.Response:
        return self._request("POST", f"{self.base}{path}", **kw)

    # ---------------------------------------------------------------- health
    def ping(self) -> bool:
        try:
            return self._get("/system_stats", retry=False, timeout=10).status_code == 200
        except Exception:  # noqa: BLE001
            return False

    # ------------------------------------------------------------- introspection
    def system_stats(self) -> dict:
        r = self._get("/system_stats", retry=False, timeout=15)
        r.raise_for_status()
        return r.json()

    def queue_info(self) -> dict:
        # Short on purpose: this is asked of every node before every job,
        # and a card that has stopped answering has to be found out about
        # quickly - the alternative is waiting out a render on a card that
        # will never answer.
        r = self._get("/queue", retry=False, timeout=10)
        r.raise_for_status()
        d = r.json()
        return {"running": len(d.get("queue_running", [])),
                "pending": len(d.get("queue_pending", []))}

    def object_info(self, class_type: Optional[str] = None) -> dict:
        path = f"/object_info/{class_type}" if class_type else "/object_info"
        r = self._get(path, retry=False, timeout=60)
        r.raise_for_status()
        return r.json()

    def available_node_types(self) -> set[str]:
        if not hasattr(self, "_node_types") or self._node_types is None:
            self._node_types = set(self.object_info().keys())
        return self._node_types

    def bypass_unsupported(self, graph: dict) -> list[str]:
        """Take out the node types this card does not have, wiring around them.

        A card missing a plugin should still be able to work. The usual
        case is the attention patch: without it the card renders the same
        picture about a third slower, which is a different plan, not a
        broken one. Such a node is removed and its users are pointed at
        what fed it, so the graph keeps meaning what it meant.

        Anything that is not a plain patch is left alone: a missing
        loader would make the graph mean something else, and that has to
        be reported rather than quietly absorbed.
        """
        try:
            have = self.available_node_types()
        except Exception as e:  # noqa: BLE001
            log.debug("读节点类型失败，跳过兼容性处理: %s", e)
            return []
        dropped: list[str] = []
        for nid, node in list(graph.items()):
            ct = node.get("class_type")
            if not ct or ct in have:
                continue
            if not bypassable(node):
                continue
            model_in = (node.get("inputs") or {}).get("model")
            if not (isinstance(model_in, list) and len(model_in) == 2):
                continue
            for other in graph.values():
                oi = other.get("inputs")
                if not isinstance(oi, dict):
                    continue
                for k, v in list(oi.items()):
                    if (isinstance(v, list) and len(v) == 2
                            and str(v[0]) == str(nid) and v[1] == 0):
                        oi[k] = list(model_in)
            graph.pop(nid, None)
            dropped.append(f"#{nid} {ct}")
        if dropped:
            log.warning("这张卡没有 %s，已绕开（渲染结果不变，速度会慢）",
                        "、".join(dropped))
        return dropped

    def list_checkpoints(self) -> list[str]:
        """Checkpoints the server actually has (for config sanity)."""
        try:
            info = self.object_info("CheckpointLoaderSimple")
            ck = info.get("CheckpointLoaderSimple", {})
            return ck.get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
        except Exception:  # noqa: BLE001
            return []

    def list_model_files(self) -> dict[str, list[str]]:
        """Model files the server can actually see, per folder.

        FLUX-style architectures split the model across diffusion_models /
        text_encoders / vae, so checking only `checkpoints` misses everything.
        """
        wanted = {
            "checkpoints": ("CheckpointLoaderSimple", "ckpt_name"),
            "diffusion_models": ("UNETLoader", "unet_name"),
            "text_encoders": ("CLIPLoader", "clip_name"),
            "vae": ("VAELoader", "vae_name"),
            "loras": ("LoraLoaderModelOnly", "lora_name"),
        }
        out: dict[str, list[str]] = {}
        for folder, (node_type, param) in wanted.items():
            try:
                info = self.object_info(node_type)
                node = info.get(node_type, {})
                req = node.get("input", {}).get("required", {})
                out[folder] = list(req.get(param, [[]])[0] or [])
            except Exception:  # noqa: BLE001
                out[folder] = []
        return out

    def workflow_model_files(self, rel: str, kind: str = "") -> list[tuple[str, str]]:
        """(folder, filename) pairs the workflow needs, from its loader nodes."""
        from .nodes import MODEL_LOADERS
        try:
            graph = self._load_workflow(rel, kind)
        except Exception:  # noqa: BLE001
            return []
        out: list[tuple[str, str]] = []
        seen: set[str] = set()
        for node in graph.values():
            spec = MODEL_LOADERS.get(str(node.get("class_type", "")))
            if not spec:
                continue
            folder, param = spec
            name = str((node.get("inputs") or {}).get(param) or "")
            if not name or name in seen:
                continue
            seen.add(name)
            out.append((folder, name))
        return out

    def validate_workflow(self, rel: str, nodes_map: dict, kind: str = "") -> dict:
        """Check a workflow: node types exist on the server, mapped semantic ids
        resolve. With auto_map on, stale ids are repaired from the graph."""
        report: dict = {"file": rel, "ok": True, "problems": [], "warnings": [], "nodes": 0}
        try:
            graph = self._load_workflow(rel, kind)
        except Exception as e:  # noqa: BLE001
            return {"file": rel, "ok": False, "problems": [f"无法读取工作流: {e}"],
                    "warnings": [], "nodes": 0}
        report["nodes"] = len(graph)
        info = infer_workflow(graph)
        report["kind"] = info["kind"]
        kind = kind or info["kind"]
        resolved, _, _ = self._resolved_nodes(kind, graph)
        report["inferred"] = {k: v for k, v in resolved.items() if v}
        report["warnings"].extend(info.get("warnings") or [])
        # The accelerator is a property of the file, not of the card: a
        # workflow that lost it still validates and still renders, a third
        # slower, with nothing to show for the difference. Said here so a
        # swapped or trimmed file cannot quietly cost that.
        if kind == "i2v":
            sage = sage_node(graph)
            report["sage"] = sage
            if not sage:
                report["warnings"].append(
                    "没有 SageAttention 加速节点（PathchSageAttentionKJ），"
                    "出视频会慢约 30%——确认用的是短剧专用工作流")
        try:
            have = self.available_node_types()
        except Exception as e:  # noqa: BLE001
            report["problems"].append(f"无法获取服务器节点信息(/object_info): {e}")
            report["ok"] = False
            return report
        for nid, node in graph.items():
            ct = node.get("class_type")
            if ct and ct not in have:
                if bypassable(node):
                    # a patch the card does not have: the render still
                    # works, only slower - so it is a note, not a fault
                    report["warnings"].append(
                        f"节点 {nid} 的类型 '{ct}' 服务器上没有，"
                        "会绕开该节点（结果不变，速度变慢）")
                    continue
                report["problems"].append(f"节点 {nid} 的类型 '{ct}' 服务器上没有（缺自定义节点/插件）")
                report["ok"] = False
        for sem, nid in (nodes_map or {}).items():
            if not nid:
                continue
            if str(nid) not in graph:
                if self.cfg.auto_map and resolved.get(sem):
                    report["warnings"].append(
                        f"配置项 {sem}->节点'{nid}' 不存在，已自动识别为 {resolved[sem]}")
                else:
                    report["problems"].append(f"配置项 {sem}->节点'{nid}' 在工作流里不存在")
                    report["ok"] = False
        for sem, nid in resolved.items():
            if nid and str(nid) not in graph:
                report["problems"].append(f"自动识别项 {sem}->节点'{nid}' 在工作流里不存在")
                report["ok"] = False
        return report

    def _resolved_nodes(self, kind: str, graph: dict) -> tuple[dict, dict, list[str]]:
        """Merge configured semantic node ids with ids inferred from the graph.

        Explicit ids win while they still exist; missing/stale ones fall back to
        inference. Returns (nodes, inference, ref_slots).
        """
        info = infer_workflow(graph)
        base = dict(info.get("t2i" if kind == "t2i" else "i2v") or {})
        explicit = dict(self.cfg.t2i_nodes if kind == "t2i" else self.cfg.i2v_nodes)
        merged = dict(base)
        for key, value in explicit.items():
            value = str(value or "")
            if not value:
                # Empty on purpose, not unconfigured: H3 has no negative
                # prompt and this file has no tail frame. Keeping the
                # guess here would aim a write at whatever the guess
                # found - and for a tail frame the guess is a reference
                # picture slot, so the render comes out looking right
                # while the reference it was handed is overwritten.
                merged.pop(key, None)
                continue
            if self.cfg.auto_map and value not in graph:
                continue
            merged[key] = value
        if not self.cfg.auto_map:
            merged = {k: str(v) for k, v in explicit.items() if v}
        refs = list(info.get("ref_slots") or [])
        primary = str(merged.get("ref_image") or "")
        if primary:
            refs = [primary] + [r for r in refs if r != primary]
        return merged, info, refs

    # ------------------------------------------------------------- workflow
    def _resolve_workflow_path(self, rel: str) -> Path:
        path = Path(rel) if Path(rel).is_absolute() else (self.root / rel)
        if path.exists():
            return path
        alt = Path(rel)
        return alt if alt.exists() else path

    def _load_workflow(self, rel: str, kind: str = "") -> dict:
        path = self._resolve_workflow_path(rel)
        if not path.exists():
            picked = self._pick_workflow(rel, kind)
            if picked and picked != rel:
                path = self._resolve_workflow_path(picked)
            else:
                raise FileNotFoundError(f"ComfyUI workflow not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _infer_file(self, path: Path) -> dict:
        key = str(path)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return {}
        cached = self._infer_cache.get(key)
        if cached and cached[0] == mtime:
            return cached[1]
        try:
            with open(path, "r", encoding="utf-8") as f:
                graph = json.load(f)
            info = infer_workflow(graph)
        except Exception:  # noqa: BLE001
            return {}
        self._infer_cache[key] = (mtime, info)
        return info

    def workflow_files(self) -> list[str]:
        """Every readable workflow: configured ones + config/comfyui/*.json."""
        seen: dict[str, None] = {}
        for rel in (self.cfg.t2i_workflow, self.cfg.i2v_workflow,
                    self.cfg.flf_workflow, self.cfg.upscale_workflow):
            if rel:
                p = self._resolve_workflow_path(rel)
                if p.exists():
                    seen[str(p.resolve())] = None
        for base in (self.root / "config/comfyui", Path("config/comfyui")):
            if base.exists():
                for p in sorted(base.glob("*.json")):
                    seen[str(p.resolve())] = None
        return list(seen)

    def _pick_workflow(self, configured: str, kind: str) -> str:
        """Configured path if present; otherwise the best-scoring workflow."""
        if configured and self._resolve_workflow_path(configured).exists():
            return configured
        if not self.cfg.auto_workflows:
            return configured
        best, best_score = "", -1
        for path in self.workflow_files():
            info = self._infer_file(Path(path))
            if not info:
                continue
            if kind == "t2i" and info.get("kind") != "t2i":
                continue
            if kind == "i2v" and info.get("kind") != "i2v":
                continue
            if kind == "flf" and not (info.get("i2v") or {}).get("last_image"):
                continue
            score = score_workflow(info)
            if score > best_score:
                best, best_score = path, score
        if best and kind and best != configured:
            log.info("ComfyUI 自动选用 %s 工作流: %s", kind, best)
        return best or configured

    def _node(self, graph: dict, nodes_map: dict, key: str) -> Optional[dict]:
        nid = str(nodes_map.get(key, ""))
        return graph.get(nid) if nid and nid in graph else None

    def _set(self, graph: dict, nodes_map: dict, key: str, field: str, value) -> None:
        node = self._node(graph, nodes_map, key)
        if node is not None:
            node.setdefault("inputs", {})[field] = value

    def _set_any(self, graph: dict, nodes_map: dict, key: str,
                 fields: tuple[str, ...], value) -> bool:
        """Write `value` to the first field of `fields` the node actually has.

        Loader nodes name their file differently depending on the architecture:
        SDXL uses `ckpt_name`, FLUX / FLUX 3 use `unet_name`. One semantic key
        ("checkpoint") has to cover both.
        """
        node = self._node(graph, nodes_map, key)
        if node is None:
            return False
        inputs = node.setdefault("inputs", {})
        for field in fields:
            if field in inputs:
                inputs[field] = value
                return True
        return False

    def _seed_value(self, requested: int) -> int:
        if requested is not None and requested >= 0:
            return requested
        if self.cfg.seed_mode == "fixed":
            return self.cfg.fixed_seed
        return random.randint(1, 2**31 - 1)

    # ------------------------------------------------------------- upload
    def upload_image(self, image_path: str | Path) -> str:
        """Upload a local image to ComfyUI /input; returns the server-side name.

        The name on the server has to say which picture this is.  Every
        character's sheet is called sheet.jpg, and a name taken from the
        file would put all of them at the same address on the server - the
        last upload overwrites the others and two slots of the same job end
        up holding the same face.  The name carries the picture's own
        fingerprint, so a picture that was drawn again gets a new address
        and a picture that did not change keeps the one it had.
        """
        p = Path(image_path)
        name = self._fingerprint(p) + "_" + p.name
        with open(p, "rb") as fh:
            files = {"image": (name, fh, "image/png")}
            data = {"overwrite": "true"}
            r = self._post("/upload/image", files=files, data=data, timeout=180)
        if r.status_code >= 400:
            raise ComfyUIError(f"上传图片失败 {r.status_code}: {r.text[:200]}")
        return r.json().get("name", name)

    @staticmethod
    def _fingerprint(path: Path, size: int = 10) -> str:
        """A short fingerprint of the file's content."""
        import hashlib
        h = hashlib.md5()
        try:
            with open(path, "rb") as fh:
                h.update(fh.read(1 << 20))
        except OSError:
            h.update(str(path).encode("utf-8", "replace"))
        return h.hexdigest()[:size]

    def upload_audio(self, audio_path: str | Path) -> str:
        """Upload a local audio file to ComfyUI /input; returns the name.

        The endpoint is the image one and the form field is called
        "image" - that is how ComfyUI takes any file.
        """
        p = Path(audio_path)
        with open(p, "rb") as fh:
            files = {"image": (p.name, fh, "audio/mpeg")}
            data = {"overwrite": "true", "type": "input"}
            r = self._post("/upload/image", files=files, data=data, timeout=180)
        if r.status_code >= 400:
            raise ComfyUIError(f"上传音频失败 {r.status_code}: {r.text[:200]}")
        return r.json().get("name", p.name)

    # ------------------------------------------------------------- submit
    def _queue(self, graph: dict) -> str:
        # A card that is missing a plugin still gets the work: the parts
        # that are only patches are taken out here, once, so both the
        # picture and the video go through the same door.
        self.bypass_unsupported(graph)
        payload = {"prompt": graph, "client_id": self.client_id}
        r = self._post("/prompt", json=payload, timeout=self.cfg.request_timeout)
        if r.status_code >= 400:
            raise ComfyUIError(f"ComfyUI /prompt {r.status_code}: {r.text[:500]}")
        return r.json()["prompt_id"]

    @staticmethod
    def is_oom(error: BaseException) -> bool:
        """Did the server run out of memory?

        ComfyUI unloads every model when that happens, so the next attempt
        starts from a clean slate and usually succeeds.
        """
        text = str(error).lower()
        return ("out of memory" in text or "oom" in text
                or "allocation on device" in text)

    # ------------------------------------------------------------- waiting
    def _wait(self, prompt_id: str, timeout: Optional[float] = None) -> None:
        """Wait for completion: WebSocket first, poll /history as fallback."""
        limit = timeout or self.cfg.timeout
        # A stop has to reach the card, not just this client. The render is
        # the long part of a run and nothing here can shorten it - only the
        # card can drop it. Without this, asking to stop waits out the clip
        # being drawn, which is a third of an hour for a five-second shot.
        #
        # Started whether or not the stop has already been asked for: a job
        # submitted just before the stop is waiting on its own completion,
        # and one submitted just after it would otherwise never be dropped.
        # `done` is what keeps a finished job's watcher from lingering and
        # interrupting whatever the next one puts on the card.
        stop = getattr(self, "stop_event", None)
        done = threading.Event()
        if stop is not None:
            threading.Thread(target=self._watch_stop,
                             args=(stop, done, time.time() + limit),
                             daemon=True).start()
        try:
            if self.cfg.use_websocket:
                try:
                    asyncio.run(self._wait_ws(prompt_id, limit))
                    return
                except Exception as e:  # noqa: BLE001
                    if not self.cfg.ws_fallback_to_poll:
                        raise
                    log.warning("WebSocket 进度监听失败(%s)，回退到轮询 /history",
                                str(e)[:120])
            self._wait_poll(prompt_id, limit)
        finally:
            done.set()

    def _watch_stop(self, stop, done: threading.Event, deadline: float) -> None:
        """Drop this job on the card the moment a stop is asked.

        Interrupted more than once on purpose: /interrupt only stops what
        is executing, and anything queued behind it starts the moment the
        first one goes - with its own watcher never armed, because the stop
        had already been asked by then. So this keeps asking until its own
        job is gone, and stops the instant that job finishes so it cannot
        reach the one after it.
        """
        while time.time() < deadline:
            if done.wait(2.0):
                return                      # our job is over
            if not stop.is_set():
                continue
            try:
                self._post("/interrupt", json={}, timeout=15)
                log.info("已请求 %s 中断当前渲染", self.base)
            except Exception as e:  # noqa: BLE001
                log.warning("中断 %s 失败: %s", self.base, str(e)[:140])
                return                      # the card is not answering

    def _video_timeout(self, frames: int) -> float:
        """Long videos need more than the default timeout.

        H3 at 960x544 costs roughly two seconds a frame plus the model load,
        so a fifteen-second shot takes several times longer than a five-second
        one.
        """
        return self.cfg.timeout + max(0, frames) * 3.0

    def _vram_frame_cap(self) -> int:
        """Longest shot this card can render without thrashing.

        H3 keeps its latent state resident while it samples, so a long shot
        needs more room than a short one. Measured on a 16GB RTX 5080:
        328 frames runs fine, 360 frames pushes model initialisation from
        60 seconds to 24 minutes - the card swaps between CPU and GPU
        instead of just running slowly. 24GB cards (the 3090s) take the
        full 360.
        """
        try:
            stats = self.system_stats()
            total = int((stats.get("devices") or [{}])[0].get("vram_total") or 0)
        except Exception:  # noqa: BLE001
            return 243
        for need, cap in ((22 << 30, 360), (15 << 30, 328)):
            if total >= need:
                return cap
        return 243

    async def _wait_ws(self, prompt_id: str, timeout: Optional[float] = None) -> None:
        import websockets
        ws_base = self.base.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_base}/ws?clientId={urllib.parse.quote(self.client_id)}"
        headers = self._auth_headers()
        connect_kw = {"max_size": None}
        # websockets>=14 uses additional_headers; older uses extra_headers
        try:
            cm = websockets.connect(ws_url, additional_headers=headers, **connect_kw)
        except TypeError:
            cm = websockets.connect(ws_url, extra_headers=headers, **connect_kw)
        async with cm as ws:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=timeout or self.cfg.timeout)
                if isinstance(msg, bytes):
                    continue  # preview image
                data = json.loads(msg)
                mtype = data.get("type")
                if mtype == "executing":
                    d = data.get("data", {})
                    if d.get("prompt_id") == prompt_id and d.get("node") is None:
                        return  # finished
                elif mtype == "execution_error":
                    d = data.get("data", {})
                    if d.get("prompt_id") == prompt_id:
                        raise ComfyUIError(f"ComfyUI 执行错误: {d}")
                elif mtype == "execution_interrupted":
                    d = data.get("data", {})
                    if d.get("prompt_id") == prompt_id:
                        raise ComfyUIError(f"ComfyUI 执行被中断: {d}")

    def _wait_poll(self, prompt_id: str, timeout: Optional[float] = None) -> None:
        """Poll /history until the prompt shows up with outputs (proxy-safe)."""
        limit = timeout or self.cfg.timeout
        deadline = time.time() + limit
        while time.time() < deadline:
            try:
                r = self._get(f"/history/{prompt_id}", retry=False,
                              timeout=self.cfg.request_timeout)
                if r.status_code == 200:
                    hist = r.json().get(prompt_id)
                    if hist:
                        status = hist.get("status", {})
                        if status.get("status_str") == "error":
                            raise ComfyUIError(f"ComfyUI 执行错误(prompt={prompt_id})")
                        if hist.get("outputs"):
                            return
            except ComfyUIError:
                raise
            except Exception as e:  # noqa: BLE001
                log.debug("poll error: %s", e)
            time.sleep(self.cfg.poll_interval)
        raise TimeoutError(f"ComfyUI prompt {prompt_id} 超时（{limit}s）")

    def _history(self, prompt_id: str) -> dict:
        # The card that has just made a video is busy writing it: the file
        # is being encoded and the card's event loop is inside ffmpeg, so
        # it does not answer at once.  The render is not thrown away over
        # a slow answer - the question is asked again, with patience, and
        # the wait is bounded so a card that has really died does not
        # hold the run up for ever.
        last: Optional[Exception] = None
        for i in range(8):
            try:
                r = self._get(f"/history/{prompt_id}", retry=False, timeout=45)
                if r.status_code == 200:
                    return r.json().get(prompt_id, {})
                last = ComfyUIError(f"HTTP {r.status_code}")
            except Exception as e:  # noqa: BLE001
                last = e
            time.sleep(5)
        raise ComfyUIError(f"ComfyUI 问不出结果(prompt={prompt_id}): {last}")

    def _download(self, item: dict, out_path: str) -> str:
        params = {
            "filename": item["filename"],
            "subfolder": item.get("subfolder", ""),
            "type": item.get("type", "output"),
        }
        r = self._get("/view", params=params, timeout=max(self.cfg.request_timeout, 300))
        if r.status_code >= 400:
            raise ComfyUIError(f"下载结果失败 {r.status_code}: {r.text[:200]}")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(r.content)
        return out_path

    def _collect_output(self, prompt_id: str, kinds: tuple[str, ...]) -> Optional[dict]:
        hist = self._history(prompt_id)
        outputs = hist.get("outputs", {})
        for _node_id, node_out in outputs.items():
            for kind in kinds:
                items = node_out.get(kind)
                if items:
                    return items[-1]
        return None

    # ------------------------------------------------------------- public API
    def _inject_refs(self, graph: dict, nodes_map: dict, ref_images: list[str],
                     extra: dict) -> None:
        """Upload reference images and feed them into the mapped LoadImage nodes.

        `ref_image` is the primary slot (first reference). Extra node ids listed
        in `extra["ref_node_ids"]` receive the remaining references in order.
        Workflows without such nodes ignore references (prompt-only mode).
        """
        paths = [p for p in ref_images if p and Path(p).exists()]
        if not paths:
            return
        uploaded: dict[str, str] = extra.setdefault("uploaded_refs", {})
        primary = str(nodes_map.get("ref_image") or "")
        extra_ids = [str(x) for x in (extra.get("ref_node_ids") or [])]
        slots = ([primary] if primary else []) + extra_ids
        for nid, path in zip(slots, paths):
            if nid not in graph:
                continue
            name = uploaded.get(path) or self.upload_image(path)
            uploaded[path] = name
            graph[nid].setdefault("inputs", {})["image"] = name

    def generate_image(self, prompt: str, negative: str, *, width: int, height: int,
                       seed: int, steps: int, cfg: float, out_path: str,
                       extra: Optional[dict] = None,
                       ref_images: Optional[list[str]] = None) -> str:
        extra = dict(extra or {})
        # a reference workflow takes the output size from the reference image,
        # so it only works when there is one
        want_ref = bool(ref_images) and bool(self.cfg.t2i_workflow_ref)
        wf = self._pick_workflow(
            self.cfg.t2i_workflow_ref if want_ref else self.cfg.t2i_workflow, "t2i")
        graph = copy.deepcopy(self._load_workflow(wf))
        nm, _info, ref_slots = self._resolved_nodes("t2i", graph)
        if ref_slots:
            extra.setdefault("ref_node_ids", ref_slots[1:])
        self._set(graph, nm, "positive", "text", prompt)
        self._set(graph, nm, "negative", "text", negative)
        self._inject_refs(graph, nm, ref_images or [], extra)
        real_seed = self._seed_value(seed)
        self._set(graph, nm, "seed", "seed", real_seed)
        self._set(graph, nm, "seed", "noise_seed", real_seed)
        self._set(graph, nm, "width", "width", width or self.cfg.width)
        self._set(graph, nm, "height", "height", height or self.cfg.height)
        # ModelSamplingFlux carries its own resolution (FLUX shift sampling)
        if nm.get("sampling"):
            self._set(graph, nm, "sampling", "width", width or self.cfg.width)
            self._set(graph, nm, "sampling", "height", height or self.cfg.height)
        self._set(graph, nm, "steps", "steps", steps or self.cfg.steps)
        self._set(graph, nm, "cfg", "cfg", cfg or self.cfg.cfg)
        self._set(graph, nm, "sampler", "sampler_name", extra.get("sampler", self.cfg.sampler))
        self._set(graph, nm, "sampler", "scheduler", extra.get("scheduler", self.cfg.scheduler))
        # model files: the loader's field name depends on the architecture
        # (ckpt_name for SDXL, unet_name for FLUX / FLUX 3)
        self._set_any(graph, nm, "checkpoint", ("ckpt_name", "unet_name"),
                      extra.get("checkpoint", self.cfg.checkpoint))
        if self.cfg.clip_name:
            self._set_any(graph, nm, "clip", ("clip_name",), self.cfg.clip_name)
        if self.cfg.vae_name:
            self._set_any(graph, nm, "vae", ("vae_name",), self.cfg.vae_name)
        for nid, fields in (extra.get("graph_overrides") or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)
        for nid, fields in (self.graph_overrides or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)

        pid = self._queue(graph)
        log.info("ComfyUI t2i 已提交 pid=%s seed=%s @ %s", pid, real_seed, self.base)
        self._wait(pid)
        item = self._collect_output(pid, ("images",))
        if not item:
            raise ComfyUIError(f"没有图片输出 pid={pid}")
        return self._download(item, out_path)

    def generate_video(self, prompt: str, negative: str, *, image_path: str = "",
                       frames: int = 32, fps: int = 16, seed: int = -1,
                       out_path: str = "", extra: Optional[dict] = None,
                       last_image_path: str = "") -> str:
        extra = dict(extra or {})
        use_flf = False
        nm: dict = {}
        graph: dict = {}
        if last_image_path and Path(last_image_path).exists():
            wf = self._pick_workflow(self.cfg.flf_workflow or self.cfg.i2v_workflow, "flf")
            if wf and self._resolve_workflow_path(wf).exists():
                try:
                    trial = copy.deepcopy(self._load_workflow(wf))
                    trial_map, _info, _refs = self._resolved_nodes("i2v", trial)
                    if trial_map.get("last_image"):
                        graph, nm, use_flf = trial, trial_map, True
                except Exception as e:  # noqa: BLE001
                    log.warning("首尾帧工作流读取失败(%s)，改用单图 i2v", str(e)[:120])
        if not use_flf:
            wf = self._pick_workflow(self.cfg.i2v_workflow, "i2v")
            graph = copy.deepcopy(self._load_workflow(wf))
            nm, _info, _refs = self._resolved_nodes("i2v", graph)
        self._set(graph, nm, "positive", "text", prompt)
        self._set(graph, nm, "positive", "prompt", prompt)  # MiniMax H3 native node uses "prompt"; others ignore it
        self._set(graph, nm, "negative", "text", negative)
        if image_path and Path(image_path).exists():
            server_name = extra.get("uploaded_image") or self.upload_image(image_path)
            extra["uploaded_image"] = server_name
            self._set(graph, nm, "image", "image", server_name)
        # the pictures: the character sheets, the room and the frame the
        # shot continues from. The workflow says which load node is which
        # slot, so the order is the one both sides agreed on.
        pictures = list(extra.get("ref_pictures") or [])
        slots: list[tuple[str, str]] = []
        ref_node = None
        ref_shape = "flat"
        for nid, node in graph.items():
            if not isinstance(node, dict):
                continue
            if "ReferenceToVideo" in str(node.get("class_type", "")):
                ref_node = node
                imgs, ref_shape = _ref_slots(node, "ref_images")
                for slot, link in sorted(imgs.items()):
                    if isinstance(link, list) and link:
                        slots.append((str(link[0]), slot))
                break
        used: set[str] = set()
        for (load_id, slot), path in zip(slots, pictures):
            if load_id not in graph or not Path(path).exists():
                continue
            graph[load_id].setdefault("inputs", {})["image"] = self.upload_image(path)
            used.add(slot)
        # The slots that got no picture are taken out of the job: the
        # node behind them would go on loading the placeholder, and the
        # model would be handed a picture that is not there. The node
        # goes too - a loader still in the graph is still validated,
        # and one with no picture of its own fails validation, which
        # refuses the whole job rather than just the extra slot.
        #
        # This happens whether there were pictures or not: a shot with no
        # reference at all - an empty room, a street with nobody in it -
        # used to keep its empty loaders, and the whole job came back as
        # a 400 with the card's time wasted.
        if ref_node is not None:
            imgs, _shape = _ref_slots(ref_node, "ref_images")
            dropped: list[str] = []
            for slot in list(imgs):
                if slot not in used:
                    link = imgs.pop(slot)
                    if isinstance(link, list) and link:
                        dropped.append(str(link[0]))
            _put_ref_slots(ref_node, "ref_images", imgs, ref_shape)
            for nid in dropped:
                graph.pop(nid, None)
        # the voice reference: the recording of the line goes in as the
        # timbre the character speaks with
        ref_audio = extra.get("ref_audio_path")
        slot = str(extra.get("ref_audio_node") or "")
        have_audio = bool(ref_audio and slot and Path(ref_audio).exists())
        if have_audio:
            server_audio = extra.get("uploaded_audio") or self.upload_audio(ref_audio)
            extra["uploaded_audio"] = server_audio
            graph.setdefault(slot, {}).setdefault("inputs", {})["audio"] = server_audio
        # Every voice slot without a recording comes out of the job,
        # loader and all - for the same reason as the pictures: a LoadAudio
        # holding no file fails the card's validation and takes the whole
        # job with it, rather than just the reference being left out. A
        # shot with no voice at all reaches this with nothing to fill.
        drop_audio: list[str] = []
        for nid, node in graph.items():
            if not isinstance(node, dict):
                continue
            if "ReferenceToVideo" not in str(node.get("class_type", "")):
                continue
            auds, shape = _ref_slots(node, "ref_audios")
            for aslot in list(auds):
                if not (have_audio and str(auds[aslot][0]) == slot):
                    link = auds.pop(aslot)
                    if isinstance(link, list) and link:
                        drop_audio.append(str(link[0]))
            _put_ref_slots(node, "ref_audios", auds, shape)
        for nid in drop_audio:
            graph.pop(nid, None)
        if use_flf:
            last_name = (extra.get("uploaded_last_image")
                         or self.upload_image(last_image_path))
            extra["uploaded_last_image"] = last_name
            self._set(graph, nm, "last_image", "image", last_name)
        real_seed = self._seed_value(seed)
        self._set(graph, nm, "seed", "seed", real_seed)
        self._set(graph, nm, "seed", "noise_seed", real_seed)
        frames = min(frames or self.cfg.frames, self._vram_frame_cap())
        self._set(graph, nm, "frames", "length", frames)
        self._set(graph, nm, "frames", "frames", frames)
        self._set(graph, nm, "frames", "batch_size", frames)
        self._set(graph, nm, "frames", "context_length", frames)
        self._set(graph, nm, "fps", "frame_rate", fps or self.cfg.fps)
        self._set(graph, nm, "fps", "fps", fps or self.cfg.fps)
        # video resolution (H3 takes it on the model node itself)
        if self.cfg.video_width and self.cfg.video_height:
            self._set(graph, nm, "width", "width", self.cfg.video_width)
            self._set(graph, nm, "height", "height", self.cfg.video_height)
        for nid, fields in (extra.get("graph_overrides") or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)
        # this node's own weights
        for nid, fields in (self.graph_overrides or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)

        pid = self._queue(graph)
        # Which card and which file served this, and whether the card's own
        # accelerator is in the graph. A render without SageAttention is
        # the same picture at a third more time, and it looks identical in
        # every other respect - so it is named here, where it can be seen
        # without reading the workflow.
        sage = sage_node(graph)
        log.info("ComfyUI i2v 已提交 pid=%s seed=%s @ %s 工作流=%s SageAttention=%s",
                 pid, real_seed, self.base,
                 Path(wf).name if not use_flf else f"{wf}(flf)",
                 f"#{sage}" if sage else "**无（会慢约 30%）**")
        self._wait(pid, timeout=self._video_timeout(frames or self.cfg.frames))
        item = self._collect_output(pid, ("gifs", "videos", "images"))
        if not item:
            raise ComfyUIError(f"没有视频输出 pid={pid}")
        return self._download(item, out_path)


def build_visual(cfg: ComfyUIConfig, root: Optional[Path] = None) -> Optional[BaseImageVideo]:
    if not cfg.enabled:
        return None
    return ComfyUIClient(cfg, root)
