"""Provider factory: build the right backend from config."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..config import Config
from .base import BaseImageVideo, BaseLLM, BaseMusic, BaseTTS
from .comfyui import ComfyUIClient, build_visual
from .llm import OpenAICompatLLM, build_llm
from .music import build_music
from .pool import ComfyUIPool, build_pool
from .tts import build_tts, resolve_voice

__all__ = [
    "BaseLLM", "BaseTTS", "BaseImageVideo", "BaseMusic",
    "OpenAICompatLLM", "ComfyUIClient", "ComfyUIPool",
    "build_llm", "build_tts", "build_visual", "build_music", "resolve_voice",
    "build_pool", "Providers",
]


class Providers:
    """Bundles every backend for one run. Lazily construct what you need."""

    def __init__(self, cfg: Config, root: Optional[Path] = None):
        self.cfg = cfg
        self.root = root or Path(".")
        self._llm: Optional[BaseLLM] = None
        self._llm_roles: dict[str, BaseLLM] = {}
        self._tts: Optional[BaseTTS] = None
        self._visual: Optional[BaseImageVideo] = None
        self._music: Optional[BaseMusic] = None
        # every client is told when a run is asked to stop, so a long
        # model call lets go at once instead of at its end
        self._stop = None

    @property
    def llm(self) -> BaseLLM:
        if self._llm is None:
            self._llm = build_llm(self.cfg.llm)
        return self._llm

    @property
    def tts(self) -> BaseTTS:
        if self._tts is None:
            self._tts = build_tts(self.cfg.tts)
        return self._tts

    @property
    def visual(self) -> Optional[BaseImageVideo]:
        if self._visual is None and self.cfg.comfyui.enabled:
            # with extra nodes in the fleet, dispatch by role and queue depth
            if self.cfg.comfyui.nodes:
                self._visual = build_pool(self.cfg, self.root)
            else:
                self._visual = build_visual(self.cfg.comfyui, self.root)
        return self._visual

    @property
    def music(self) -> BaseMusic:
        if self._music is None:
            self._music = build_music(self.cfg.music, self.root)
        return self._music

    def bind_stop(self, event) -> None:
        """Tell every client, present and future, that a stop can happen."""
        self._stop = event
        for client in [self._llm, *self._llm_roles.values()]:
            if client is not None:
                client.stop_event = event
        # The renderers too. A clip is minutes long and the card holds it
        # until it is finished, so a stop only the language clients can
        # hear waits out the clip - and asking the card to drop its job is
        # the only thing that makes a stop land now.
        try:
            vis = self.visual
        except Exception:  # noqa: BLE001
            return
        if vis is None:
            return
        # The pool itself has to hear it too: it is the one that waits
        # for a card, and a stop that lands while it is waiting would
        # otherwise not be noticed until the wait is over.
        vis.stop_event = event
        nodes = getattr(vis, "nodes", None)
        if nodes:
            for node in nodes:
                client = getattr(node, "client", None)
                if client is not None:
                    client.stop_event = event

    def llm_for(self, stage: str) -> BaseLLM:
        """LLM for a pipeline stage, resolved through the model registry.

        With a registry, each stage gets the model that claims it (by priority,
        default fallback). Without one, keep the legacy single endpoint plus
        per-stage `llm.model_overrides`.
        """
        if self.cfg.models.entries:
            if stage not in self._llm_roles:
                client = build_llm(self.cfg.resolve_llm(stage))
                client.stop_event = self._stop
                self._llm_roles[stage] = client
            return self._llm_roles[stage]
        base = self.llm
        if isinstance(base, OpenAICompatLLM):
            return base.for_stage(stage)
        return base
