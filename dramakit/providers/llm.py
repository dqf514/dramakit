"""OpenAI-compatible LLM client.

Works with any /v1/chat/completions endpoint:
  - Cloud: OpenAI, DeepSeek, 通义千问(DashScope), Kimi(月之暗面), Groq, 智谱...
  - Local: Ollama  (http://localhost:11434/v1)
           LM Studio (http://localhost:1234/v1)
           vLLM / llama.cpp server

Implemented directly on httpx so no vendor SDK is required.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx
from tenacity import (Retrying, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

from ..config import LLMConfig
from .base import BaseLLM, LLMResponse

log = logging.getLogger("dramakit.llm")


class RetryableLLMError(Exception):
    pass


class OpenAICompatLLM(BaseLLM):
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.base_url = cfg.base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            # tolerate both ".../v1" and ".../v1/" and bare host
            if "/v1" not in self.base_url:
                self.base_url += "/v1"
        self.headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            self.headers["Authorization"] = f"Bearer {cfg.api_key}"

    def _model(self, override: Optional[str]) -> str:
        return override or self.cfg.model

    def _post(self, payload: dict) -> dict:
        attempts = max(1, self.cfg.max_retries + 1)
        for attempt in Retrying(
            retry=retry_if_exception_type((RetryableLLMError, httpx.TransportError)),
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=1.5, min=2, max=30),
            reraise=True,
        ):
            with attempt:
                return self._post_once(payload)

    def _post_once(self, payload: dict) -> dict:
        try:
            with httpx.Client(timeout=self.cfg.timeout,
                              trust_env=self.cfg.use_proxy) as client:
                r = client.post(f"{self.base_url}/chat/completions",
                                json=payload, headers=self.headers)
        except httpx.TransportError as e:
            raise RetryableLLMError(f"transport error: {e}") from e
        if r.status_code in (429, 500, 502, 503, 504):
            raise RetryableLLMError(f"HTTP {r.status_code}: {r.text[:200]}")
        if r.status_code >= 400:
            raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:400]}")
        return r.json()

    def complete(self, system: str, user: str, *, temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None, json_mode: bool = False,
                 model: Optional[str] = None) -> LLMResponse:
        payload: dict = {
            "model": self._model(model),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.cfg.temperature if temperature is None else temperature,
            "top_p": self.cfg.top_p,
            "max_tokens": max_tokens or self.cfg.max_tokens,
            "stream": False,
        }
        if json_mode and self.cfg.json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = self._post(payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected LLM response shape: {str(data)[:300]}")
        usage = data.get("usage", {}) or {}
        return LLMResponse(
            text=text or "",
            model=data.get("model", payload["model"]),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    def for_stage(self, stage: str) -> "OpenAICompatLLM":
        """Return a shallow clone with the stage-specific model override applied."""
        override = self.cfg.model_overrides.get(stage)
        if not override:
            return self
        clone = OpenAICompatLLM(self.cfg)
        clone._stage_model = override  # type: ignore[attr-defined]
        orig_model = self.cfg.model

        def _model(o: Optional[str]) -> str:  # noqa: ANN001
            return o or override or orig_model
        clone._model = _model  # type: ignore[method-assign]
        return clone


def build_llm(cfg: LLMConfig) -> BaseLLM:
    return OpenAICompatLLM(cfg)
