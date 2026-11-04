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
import threading
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
# how long a node that did not answer is left alone
SILENT_TTL = 120.0
# what a silent node's queue depth is reported as - deep enough that no
# other node is preferred to it
SILENT_DEPTH = 999
# how long a job waits for a card that is busy before giving up
DISPATCH_WAIT = 3600.0


class _Node:
    """One member of the fleet."""

    def __init__(self, spec: NodeConfig, cfg: ComfyUIConfig, root: Path):
        self.spec = spec
        self.client = ComfyUIClient(cfg, root)
        self.roles = {r.strip().lower() for r in (spec.roles or []) if r.strip()}
        self._queue: tuple[float, int] = (0.0, 0)
        self._silent_until: float = 0.0

    @property
    def max_concurrent(self) -> int:
        """How many jobs this card can do at once.

        One card is one GPU, and one H3 job fills it. Two jobs on one card
        do not run side by side: they take turns, and each one takes
        three times as long - so the pair is slower than one alone, and
        the second one looks like a card that has gone slow.
        """
        return max(1, int(getattr(self.spec, "max_concurrent", 1) or 1))

    @property
    def name(self) -> str:
        return self.spec.name

    def takes(self, role: str) -> bool:
        return not self.roles or role in self.roles

    @property
    def silent(self) -> bool:
        """True while this node is not answering."""
        return time.time() < self._silent_until

    def depth(self) -> int:
        """Queued + running jobs, cached briefly.

        A node that does not answer is not idle. It is worse than idle:
        a job sent to it never comes back, and the run waits out the whole
        timeout before trying anywhere else - so every clip pays for the
        silent card first, and the card that is working gets the second
        one. A failure is therefore reported as a queue deep enough that
        no other node is preferred, and the node is left alone for a
        while so it gets a chance to come back.
        """
        now = time.time()
        if now - self._queue[0] < QUEUE_TTL:
            return self._queue[1]
        try:
            q = self.client.queue_info()
            depth = int(q.get("running", 0)) + int(q.get("pending", 0))
            self._silent_until = 0.0
        except Exception as e:  # noqa: BLE001
            log.warning("节点 %s 队列不可达（%s），暂时不往它身上派活",
                        self.name, str(e)[:120])
            depth = SILENT_DEPTH
            self._silent_until = now + SILENT_TTL
        self._queue = (now, depth)
        return depth

    def forget_queue(self) -> None:
        """Drop the cached queue reading so the next pick re-measures."""
        self._queue = (0.0, 0)


class ComfyUIPool(BaseImageVideo):
    """A fleet of ComfyUI servers with role-based dispatch."""

    def __init__(self, nodes: list[_Node]):
        self.nodes = nodes
        # jobs we have sent and not yet got back
        self._inflight: dict[str, int] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------- selection
    def candidates(self, role: str) -> list[_Node]:
        """Nodes that can take this role, least busy first."""
        ok = [n for n in self.nodes if n.takes(role)]
        return sorted(ok, key=lambda n: (self.busy(n), n.name))

    def busy(self, node: _Node) -> int:
        """How much this node has on: what it says plus what we sent it."""
        return node.depth() + self._inflight.get(node.name, 0)

    def _take(self, role: str, skip: set[str]) -> Optional[_Node]:
        """Pick the least busy node and count the job on it, together.

        A node that has stopped answering is only used when every other
        one has stopped too: it is the last choice, not the first, because
        a job sent to a silent card is a job that never comes back.

        A card takes one job at a time. Two H3 jobs on one 16GB card do not
        run side by side - they take turns, and each one takes three times
        as long, so the pair is slower than one alone. So a node that is
        already at its limit is not a candidate at all; the work waits for
        it rather than being put on top of it.

        How busy a card is is the card's own answer, not this process's:
        a job that was running when the console was restarted is still
        running on the card, and the card knows it even though nobody
        here does. So the two counts are taken together and the larger
        one is believed.
        """
        def _on(node: _Node) -> int:
            return max(self._inflight.get(node.name, 0), node.depth())

        ok = [n for n in self.nodes
              if n.takes(role) and n.name not in skip
              and _on(n) < n.max_concurrent]
        if not ok:
            return None
        alive = [n for n in ok if not n.silent]
        pool = alive or ok
        node = min(pool, key=lambda n: (self.busy(n), n.name))
        self._inflight[node.name] = self._inflight.get(node.name, 0) + 1
        return node

    def _stopped(self) -> bool:
        """Has a stop been asked for?"""
        ev = getattr(self, "stop_event", None)
        try:
            return bool(ev is not None and ev.is_set())
        except Exception:  # noqa: BLE001
            return False

    def _dispatch(self, role: str, fn) -> str:
        """Give the job to a card that can take it.

        Two kinds of "no card" have to be told apart. A card that is busy
        is worth waiting for - the work will be done in a few minutes. A
        card that has failed is not: if every card has failed, waiting
        only delays the news that there is no card.

        And a stop ends the wait wherever it is: a run that has been
        asked to stop should not sit here for an hour because the card
        it wants is busy with something else.
        """
        tried: list[str] = []
        last: Optional[Exception] = None
        deadline = time.time() + DISPATCH_WAIT
        while True:
            with self._lock:
                node = self._take(role, set(tried))
            if node is None:
                if len(tried) >= len(self.nodes):
                    # every card has been tried and every one failed
                    break
                if self._stopped() or time.time() > deadline:
                    break
                # every card is busy: wait for one and look again
                time.sleep(2.0)
                continue
            tried.append(node.name)
            try:
                return fn(node.client)
            except Exception as e:  # noqa: BLE001
                last = e
                log.warning("节点 %s 渲染失败，转移: %s", node.name, str(e)[:160])
                node.forget_queue()
                if self._stopped():
                    break
            finally:
                with self._lock:
                    self._inflight[node.name] = max(
                        0, self._inflight.get(node.name, 0) - 1)
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
    local.roles = list(getattr(base, "local_roles", None) or [])
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
        node_cfg.graph_overrides = dict(spec.graph_overrides or {})
        # A node may run its own workflow: two cards on one box can be given
        # different files for the same kind of work, and the global setting
        # only says what that kind of work uses by default.
        for role, rel in (spec.workflows or {}).items():
            rel = str(rel or "").strip()
            if not rel:
                continue
            if role == "t2i":
                node_cfg.t2i_workflow = rel
            elif role == "i2v":
                node_cfg.i2v_workflow = rel
            elif role == "flf":
                node_cfg.flf_workflow = rel
        nodes.append(_Node(spec, node_cfg, root))

    if not nodes:
        return None
    log.info("渲染节点池: %s", ", ".join(f"{n.name}({'/'.join(sorted(n.roles)) or 'any'})"
                                       for n in nodes))
    return ComfyUIPool(nodes)
