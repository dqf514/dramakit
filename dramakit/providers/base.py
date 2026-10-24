"""Provider interfaces. Every AI capability is behind one of these so cloud and
local backends are drop-in interchangeable."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    text: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


class BaseLLM(abc.ABC):
    @abc.abstractmethod
    def complete(self, system: str, user: str, *, temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None, json_mode: bool = False,
                 model: Optional[str] = None) -> LLMResponse:
        ...

    def complete_json(self, system: str, user: str, **kw) -> dict | list:
        """complete() + robust JSON extraction (tolerates ```json fences)."""
        import json, re
        raw = self.complete(system, user, json_mode=True, **kw).text
        raw = raw.strip()
        # strip code fences
        m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if m:
            raw = m.group(1).strip()
        # grab first {...} or [...] if extra prose leaked in
        if not (raw.startswith("{") or raw.startswith("[")):
            m = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
            if m:
                raw = m.group(1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # last resort: fix trailing commas
            raw2 = re.sub(r",\s*([}\]])", r"\1", raw)
            return json.loads(raw2)


class BaseTTS(abc.ABC):
    @abc.abstractmethod
    def synthesize(self, text: str, voice: str, out_path: str, *,
                   rate: str = "+0%", volume: str = "+0%", pitch: str = "+0Hz",
                   speed: float = 1.0, emotion: str = "") -> float:
        """Write audio to out_path, return duration in seconds."""
        ...

    def list_voices(self) -> list[str]:
        return []


class BaseImageVideo(abc.ABC):
    """Generates a still image and/or a video clip for one shot."""

    @abc.abstractmethod
    def generate_image(self, prompt: str, negative: str, *, width: int, height: int,
                       seed: int, steps: int, cfg: float, out_path: str,
                       extra: Optional[dict] = None,
                       ref_images: Optional[list[str]] = None) -> str:
        ...

    def generate_video(self, prompt: str, negative: str, *, image_path: str = "",
                       last_image_path: str = "", frames: int = 32, fps: int = 16,
                       seed: int = -1, out_path: str = "",
                       extra: Optional[dict] = None) -> str:
        raise NotImplementedError("This provider does not support video generation.")


class BaseMusic(abc.ABC):
    @abc.abstractmethod
    def get_track(self, mood: str, duration: float, out_path: str) -> Optional[str]:
        """Produce/copy a BGM track matching `mood`; return path or None."""
        ...
