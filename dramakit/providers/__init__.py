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

    def llm_for(self, stage: str) -> BaseLLM:
        """LLM for a pipeline stage, resolved through the model registry.

        With a registry, each stage gets the model that claims it (by priority,
        default fallback). Without one, keep the legacy single endpoint plus
        per-stage `llm.model_overrides`.
        """
        if self.cfg.models.entries:
            if stage not in self._llm_roles:
                self._llm_roles[stage] = build_llm(self.cfg.resolve_llm(stage))
            return self._llm_roles[stage]
        base = self.llm
        if isinstance(base, OpenAICompatLLM):
            return base.for_stage(stage)
        return base
