"""Dispatch a render to the right ComfyUI node.

The fleet is a list of ComfyUI servers. Each may declare what it is for
(`roles`: t2i / i2v). A still goes to a node that does stills, a video to a
node that does video, and a node with no roles takes anything.

Within the eligible nodes the one with the shortest queue wins, so work
spreads over the fleet instead of piling onto whichever node answered first.
If a node fails mid-render the job moves to the next candidate.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from ..config import Config, ComfyUIConfig, NodeConfig
from .base import BaseImageVideo
from .comfyui import ComfyUIClient, ComfyUIError

log = logging.getLogger("dramakit.pool")

ROLE_T2I = "t2i"
ROLE_I2V = "i2v"

# how long a queue-depth reading stays valid
QUEUE_TTL = 3.0


class _Node:
    """One member of the fleet."""

    def __init__(self, spec: NodeConfig, cfg: ComfyUIConfig, root: Path):
        self.spec = spec
        self.client = ComfyUIClient(cfg, root)
        self.roles = {r.strip().lower() for r in (spec.roles or []) if r.strip()}
        self._queue: tuple[float, int] = (0.0, 0)

    @property
    def name(self) -> str:
        return self.spec.name

    def takes(self, role: str) -> bool:
        return not self.roles or role in self.roles

    def depth(self) -> int:
        """Queued + running jobs, cached briefly."""
        now = time.time()
        if now - self._queue[0] < QUEUE_TTL:
            return self._queue[1]
        depth = 0
        try:
            q = self.client.queue_info()
            depth = int(q.get("running", 0)) + int(q.get("pending", 0))
        except Exception as e:  # noqa: BLE001
            log.debug("节点 %s 队列不可达: %s", self.name, e)
            depth = 0
        self._queue = (now, depth)
        return depth

    def forget_queue(self) -> None:
        """Drop the cached queue reading so the next pick re-measures."""
        self._queue = (0.0, 0)


class ComfyUIPool(BaseImageVideo):
    """A fleet of ComfyUI servers with role-based dispatch."""

    def __init__(self, nodes: list[_Node]):
        self.nodes = nodes

    # ------------------------------------------------------------- selection
    def candidates(self, role: str) -> list[_Node]:
        """Nodes that can take this role, least busy first."""
        ok = [n for n in self.nodes if n.takes(role)]
        return sorted(ok, key=lambda n: (n.depth(), n.name))

    def _dispatch(self, role: str, fn) -> str:
        tried: list[str] = []
        last: Optional[Exception] = None
        for node in self.candidates(role):
            tried.append(node.name)
            try:
                return fn(node.client)
            except Exception as e:  # noqa: BLE001
                last = e
                log.warning("节点 %s 渲染失败，转移: %s", node.name, str(e)[:160])
                node.forget_queue()
        raise ComfyUIError(
            f"没有可用的渲染节点（任务={role}，尝试过 {', '.join(tried) or '无'}）"
            + (f"：{last}" if last else ""))

    # --------------------------------------------------------------- render
    def generate_image(self, prompt: str, negative: str, *, width: int, height: int,
                       seed: int, steps: int, cfg: float, out_path: str,
                       extra: Optional[dict] = None,
                       ref_images: Optional[list[str]] = None) -> str:
        def run(client: ComfyUIClient) -> str:
            return client.generate_image(
                prompt, negative, width=width, height=height, seed=seed,
                steps=steps, cfg=cfg, out_path=out_path, extra=extra,
                ref_images=ref_images)

        return self._dispatch(ROLE_T2I, run)

    def generate_video(self, prompt: str, negative: str, *, image_path: str = "",
                       frames: int = 32, fps: int = 16, seed: int = -1,
                       out_path: str = "", extra: Optional[dict] = None,
                       last_image_path: str = "") -> str:
        def run(client: ComfyUIClient) -> str:
            return client.generate_video(
                prompt, negative, image_path=image_path, frames=frames, fps=fps,
                seed=seed, out_path=out_path, extra=extra,
                last_image_path=last_image_path)

        return self._dispatch(ROLE_I2V, run)

    def get_track(self, mood: str, duration: float, out_path: str) -> Optional[str]:
        return None

    def ping(self) -> bool:
        """True when at least one node in the fleet answers."""
        return any(n.client.ping() for n in self.nodes)

    # ---------------------------------------------------------------- health
    def health(self) -> list[dict]:
        out = []
        for node in self.nodes:
            try:
                online = node.client.ping()
                stats = node.client.system_stats() if online else {}
            except Exception:  # noqa: BLE001
                online, stats = False, {}
            out.append({"name": node.name, "base_url": node.spec.base_url,
                        "roles": sorted(node.roles), "online": online,
                        "depth": node.depth(), "stats": stats})
        return out


def build_pool(cfg: Config, root: Optional[Path] = None) -> Optional[ComfyUIPool]:
    """Build the fleet from config: the local ComfyUI plus every extra node."""
    base = cfg.comfyui
    root = Path(root) if root else Path(".")
    nodes: list[_Node] = []

    local = NodeConfig(name="local", base_url=base.base_url,
                       auth=base.auth if base.auth in ("none", "basic", "bearer") else "none",
                       auth_username=base.auth_username,
                       auth_password=base.auth_password,
                       auth_token=base.auth_token,
                       extra_headers=base.extra_headers,
                       verify_tls=base.verify_tls)
    local_cfg = base.model_copy()
    nodes.append(_Node(local, local_cfg, root))

    for spec in (base.nodes or []):
        if not spec.enabled:
            continue
        # the extra nodes share the workflow/model config; only the endpoint differs
        node_cfg = base.model_copy()
        node_cfg.base_url = spec.base_url
        node_cfg.auth = spec.auth if spec.auth in ("none", "basic", "bearer") else "none"
        node_cfg.auth_username = spec.auth_username
        node_cfg.auth_password = spec.auth_password
        node_cfg.auth_token = spec.auth_token
        node_cfg.extra_headers = spec.extra_headers or {}
        node_cfg.verify_tls = spec.verify_tls
        nodes.append(_Node(spec, node_cfg, root))

    if not nodes:
        return None
    log.info("渲染节点池: %s", ", ".join(f"{n.name}({'/'.join(sorted(n.roles)) or 'any'})"
                                       for n in nodes))
    return ComfyUIPool(nodes)
