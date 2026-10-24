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
        return set(self.object_info().keys())

    def list_checkpoints(self) -> list[str]:
        """Checkpoints the server actually has (for config sanity)."""
        try:
            info = self.object_info("CheckpointLoaderSimple")
            ck = info.get("CheckpointLoaderSimple", {})
            return ck.get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
        except Exception:  # noqa: BLE001
            return []

    def validate_workflow(self, rel: str, nodes_map: dict) -> dict:
        """Check a workflow file: every node's class_type exists on the server and
        every mapped semantic node id is present. Returns a report dict."""
        report: dict = {"file": rel, "ok": True, "problems": [], "nodes": 0}
        try:
            graph = self._load_workflow(rel)
        except Exception as e:  # noqa: BLE001
            return {"file": rel, "ok": False, "problems": [f"无法读取工作流: {e}"], "nodes": 0}
        report["nodes"] = len(graph)
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
            if str(nid) not in graph:
                report["problems"].append(f"配置项 {sem}->节点'{nid}' 在工作流里不存在")
                report["ok"] = False
        return report

    # ------------------------------------------------------------- workflow
    def _load_workflow(self, rel: str) -> dict:
        path = (self.root / rel) if not Path(rel).is_absolute() else Path(rel)
        if not path.exists():
            alt = Path(rel)
            if alt.exists():
                path = alt
            else:
                raise FileNotFoundError(f"ComfyUI workflow not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _node(self, graph: dict, nodes_map: dict, key: str) -> Optional[dict]:
        nid = str(nodes_map.get(key, ""))
        return graph.get(nid) if nid and nid in graph else None

    def _set(self, graph: dict, nodes_map: dict, key: str, field: str, value) -> None:
        node = self._node(graph, nodes_map, key)
        if node is not None:
            node.setdefault("inputs", {})[field] = value

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
    def _wait(self, prompt_id: str) -> None:
        """Wait for completion: WebSocket first, poll /history as fallback."""
        if self.cfg.use_websocket:
            try:
                asyncio.run(self._wait_ws(prompt_id))
                return
            except Exception as e:  # noqa: BLE001
                if not self.cfg.ws_fallback_to_poll:
                    raise
                log.warning("WebSocket 进度监听失败(%s)，回退到轮询 /history", str(e)[:120])
        self._wait_poll(prompt_id)

    async def _wait_ws(self, prompt_id: str) -> None:
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
                msg = await asyncio.wait_for(ws.recv(), timeout=self.cfg.timeout)
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

    def _wait_poll(self, prompt_id: str) -> None:
        """Poll /history until the prompt shows up with outputs (proxy-safe)."""
        deadline = time.time() + self.cfg.timeout
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
        raise TimeoutError(f"ComfyUI prompt {prompt_id} 超时（{self.cfg.timeout}s）")

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
        extra = extra or {}
        graph = copy.deepcopy(self._load_workflow(self.cfg.t2i_workflow))
        nm = self.cfg.t2i_nodes
        self._set(graph, nm, "positive", "text", prompt)
        self._set(graph, nm, "negative", "text", negative)
        self._inject_refs(graph, nm, ref_images or [], extra)
        real_seed = self._seed_value(seed)
        self._set(graph, nm, "seed", "seed", real_seed)
        self._set(graph, nm, "seed", "noise_seed", real_seed)
        self._set(graph, nm, "width", "width", width or self.cfg.width)
        self._set(graph, nm, "height", "height", height or self.cfg.height)
        self._set(graph, nm, "steps", "steps", steps or self.cfg.steps)
        self._set(graph, nm, "cfg", "cfg", cfg or self.cfg.cfg)
        self._set(graph, nm, "sampler", "sampler_name", extra.get("sampler", self.cfg.sampler))
        self._set(graph, nm, "sampler", "scheduler", extra.get("scheduler", self.cfg.scheduler))
        self._set(graph, nm, "checkpoint", "ckpt_name",
                  extra.get("checkpoint", self.cfg.checkpoint))
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
        extra = extra or {}
        nm = self.cfg.i2v_nodes
        use_flf = bool(last_image_path and Path(last_image_path).exists()
                       and self.cfg.flf_workflow)
        wf = self.cfg.flf_workflow if use_flf else self.cfg.i2v_workflow
        graph = copy.deepcopy(self._load_workflow(wf))
        self._set(graph, nm, "positive", "text", prompt)
        self._set(graph, nm, "negative", "text", negative)
        if image_path and Path(image_path).exists():
            server_name = extra.get("uploaded_image") or self.upload_image(image_path)
            extra["uploaded_image"] = server_name
            self._set(graph, nm, "image", "image", server_name)
        if use_flf:
            if not str(nm.get("last_image") or ""):
                raise ComfyUIError(
                    "首尾帧工作流已启用，但 comfyui.i2v_nodes.last_image 未配置节点 id")
            last_name = (extra.get("uploaded_last_image")
                         or self.upload_image(last_image_path))
            extra["uploaded_last_image"] = last_name
            self._set(graph, nm, "last_image", "image", last_name)
        real_seed = self._seed_value(seed)
        self._set(graph, nm, "seed", "seed", real_seed)
        self._set(graph, nm, "seed", "noise_seed", real_seed)
        self._set(graph, nm, "frames", "length", frames or self.cfg.frames)
        self._set(graph, nm, "frames", "frames", frames or self.cfg.frames)
        self._set(graph, nm, "frames", "batch_size", frames or self.cfg.frames)
        self._set(graph, nm, "frames", "context_length", frames or self.cfg.frames)
        self._set(graph, nm, "fps", "frame_rate", fps or self.cfg.fps)
        self._set(graph, nm, "fps", "fps", fps or self.cfg.fps)
        for nid, fields in (extra.get("graph_overrides") or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)

        pid = self._queue(graph)
        log.info("ComfyUI i2v 已提交 pid=%s seed=%s @ %s", pid, real_seed, self.base)
        self._wait(pid)
        item = self._collect_output(pid, ("gifs", "videos", "images"))
        if not item:
            raise ComfyUIError(f"没有视频输出 pid={pid}")
        return self._download(item, out_path)


def build_visual(cfg: ComfyUIConfig, root: Optional[Path] = None) -> Optional[BaseImageVideo]:
    if not cfg.enabled:
        return None
    return ComfyUIClient(cfg, root)
