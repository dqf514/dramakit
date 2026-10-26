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
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import httpx

from ..config import ComfyUIConfig
from .base import BaseImageVideo
from .workflow_map import infer_workflow, score_workflow

log = logging.getLogger("dramakit.comfyui")


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient(BaseImageVideo):
    def __init__(self, cfg: ComfyUIConfig, root: Optional[Path] = None):
        self.cfg = cfg
        self.root = Path(root) if root else Path(".")
        self.base = cfg.base_url.rstrip("/")
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
        r = self._get("/queue", retry=False, timeout=15)
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
        try:
            have = self.available_node_types()
        except Exception as e:  # noqa: BLE001
            report["problems"].append(f"无法获取服务器节点信息(/object_info): {e}")
            report["ok"] = False
            return report
        for nid, node in graph.items():
            ct = node.get("class_type")
            if ct and ct not in have:
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
        """Upload a local image to ComfyUI /input; returns the server-side name."""
        p = Path(image_path)
        with open(p, "rb") as fh:
            files = {"image": (p.name, fh, "image/png")}
            data = {"overwrite": "true"}
            r = self._post("/upload/image", files=files, data=data, timeout=180)
        if r.status_code >= 400:
            raise ComfyUIError(f"上传图片失败 {r.status_code}: {r.text[:200]}")
        return r.json().get("name", p.name)

    # ------------------------------------------------------------- submit
    def _queue(self, graph: dict) -> str:
        payload = {"prompt": graph, "client_id": self.client_id}
        r = self._post("/prompt", json=payload, timeout=self.cfg.request_timeout)
        if r.status_code >= 400:
            raise ComfyUIError(f"ComfyUI /prompt {r.status_code}: {r.text[:500]}")
        return r.json()["prompt_id"]

    # ------------------------------------------------------------- waiting
    def _wait(self, prompt_id: str, timeout: Optional[float] = None) -> None:
        """Wait for completion: WebSocket first, poll /history as fallback."""
        limit = timeout or self.cfg.timeout
        if self.cfg.use_websocket:
            try:
                asyncio.run(self._wait_ws(prompt_id, limit))
                return
            except Exception as e:  # noqa: BLE001
                if not self.cfg.ws_fallback_to_poll:
                    raise
                log.warning("WebSocket 进度监听失败(%s)，回退到轮询 /history", str(e)[:120])
        self._wait_poll(prompt_id, limit)

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
        r = self._get(f"/history/{prompt_id}", timeout=self.cfg.request_timeout)
        r.raise_for_status()
        return r.json().get(prompt_id, {})

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

        pid = self._queue(graph)
        log.info("ComfyUI i2v 已提交 pid=%s seed=%s @ %s", pid, real_seed, self.base)
        self._wait(pid, timeout=self._video_timeout(frames or self.cfg.frames))
        item = self._collect_output(pid, ("gifs", "videos", "images"))
        if not item:
            raise ComfyUIError(f"没有视频输出 pid={pid}")
        return self._download(item, out_path)


def build_visual(cfg: ComfyUIConfig, root: Optional[Path] = None) -> Optional[BaseImageVideo]:
    if not cfg.enabled:
        return None
    return ComfyUIClient(cfg, root)
