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
import threading
from pathlib import Path
from typing import Optional, Sequence

import httpx
from tenacity import (Retrying, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

from ..config import LLMConfig
from ..utils import mem as _mem
from .base import BaseLLM, LLMResponse

log = logging.getLogger("dramakit.llm")


class RetryableLLMError(Exception):
    pass


def _shape_error(data: object, budget: int, exc: Optional[Exception]) -> str:
    """Why an LLM response could not be read, in the reader's terms.

    The endpoint is reachable when this is raised, so the useful answer is
    what the model actually did - and for a reasoning model the common
    answer is that it thought for the whole budget and had nothing left to
    say. That is a budget to raise, not a parser to fix.
    """
    if not isinstance(data, dict) or "choices" not in data:
        return f"Unexpected LLM response shape: {str(data)[:300]}"
    choices = data.get("choices") or []
    if not choices:
        return (f"模型没有返回任何选择（max_tokens={budget}）。"
                f"推理型模型会先把 token 花在思考上，把 max_tokens 调大再试。")
    message = (choices[0] or {}).get("message") or {}
    reason = (choices[0] or {}).get("finish_reason") or ""
    thinking = len(str(message.get("reasoning_content") or ""))
    if reason == "length" or (not message.get("content") and thinking):
        return (f"模型在 {budget} 个 token 内只做了推理（{thinking} 字），没有输出正文"
                f"（finish_reason={reason or 'length'}）。把 max_tokens 调大再试。")
    if exc is not None:
        return f"Unexpected LLM response shape: {str(data)[:300]}"
    return f"模型返回了空正文: {str(data)[:300]}"


class OpenAICompatLLM(BaseLLM):
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        # Set when a run is running and someone asks it to stop. It is
        # consulted between attempts and around the request itself, so a
        # call that would hold a stage for a minute lets go at once.
        self.stop_event = None
        self.reasoning_effort = (cfg.reasoning_effort or "").strip()
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

    def _abandoned(self) -> bool:
        """Raise if the run was asked to stop while this call was in flight."""
        from ..pipeline.base import RunStopped
        if self.stop_event is not None and self.stop_event.is_set():
            raise RunStopped()

    def _post(self, payload: dict) -> dict:
        # A stop must land now, not when the request happens to finish.
        # The call is issued in a worker and the caller waits on the event
        # as well as the answer; the request carries on at the provider
        # and is paid for either way, but the run moves on immediately.
        if self.stop_event is not None:
            box: dict = {}

            def _work():
                try:
                    box["res"] = self._post_retrying(payload)
                except BaseException as e:  # noqa: BLE001
                    box["err"] = e

            th = threading.Thread(target=_work, daemon=True)
            th.start()
            while th.is_alive():
                if self.stop_event.wait(0.25):
                    self._abandoned()
                th.join(0.25)
            self._abandoned()
            if "err" in box:
                raise box["err"]
            return box["res"]
        return self._post_retrying(payload)

    def _post_retrying(self, payload: dict) -> dict:
        attempts = max(1, self.cfg.max_retries + 1)
        for attempt in Retrying(
            retry=retry_if_exception_type((RetryableLLMError, httpx.TransportError)),
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=1.5, min=2, max=30),
            reraise=True,
        ):
            with attempt:
                self._abandoned()
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
        # The size is looked at before the answer is parsed: a model that
        # starts repeating itself can send tens of megabytes, and parsing
        # that is what takes the machine's memory with it.
        size = len(r.content or b"")
        log.info("LLM 收到 %d 字节（上限 %s token）", size,
                 payload.get("max_tokens"))
        if size > 8_000_000:
            raise RuntimeError(
                f"模型的回答有 {size} 字节，太大了（这一轮的上限是 "
                f"{payload.get('max_tokens')} 个 token）。多半是在复读。")
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
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        if json_mode and self.cfg.json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = self._post(payload)
        budget = payload["max_tokens"]
        try:
            choice = data["choices"][0]
            message = choice["message"]
            text = message["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(_shape_error(data, budget, e)) from e
        if text is None:
            # A reasoning model can spend the whole budget thinking and hand
            # back reasoning_content with no content. finish_reason says so,
            # and reporting that as a malformed response sends the reader
            # looking for a parser bug that does not exist.
            raise RuntimeError(_shape_error(data, budget, None))
        # an answer that is too big is a model that started repeating
        # itself; it is said here, in words, instead of being allowed to
        # take the machine's memory with it
        if len(text or "") > 4_000_000:
            raise RuntimeError(
                f"模型的回答有 {len(text or '')} 字，太大了（这一轮的上限是 "
                f"{budget} 个 token）。多半是在复读。")
        log.info("LLM 回答 %d 字（%d token 的上限），进程用了 %.0f MB，机器还剩 %.0f MB",
                 len(text or ""), budget, _mem.rss_mb(), _mem.free_mb())
        usage = data.get("usage", {}) or {}
        return LLMResponse(
            text=text or "",
            model=data.get("model", payload["model"]),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    def complete_vision(self, system: str, user: str, images: Sequence[str],
                        *, temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None,
                        json_mode: bool = False,
                        model: Optional[str] = None) -> LLMResponse:
        """Talk to a model that can look at pictures.

        The images are JPEG files; they are sent as inline data, which is
        what the OpenAI compatible endpoints expect.
        """
        import base64
        import mimetypes

        content: list[dict] = [{"type": "text", "text": user}]
        for path in images:
            p = Path(path)
            if not p.exists():
                continue
            mime = mimetypes.guess_type(str(p))[0] or "image/jpeg"
            b64 = base64.b64encode(p.read_bytes()).decode("ascii")
            content.append({"type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"}})
        payload: dict = {
            "model": self._model(model),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "temperature": self.cfg.temperature if temperature is None else temperature,
            "top_p": self.cfg.top_p,
            "max_tokens": max_tokens or self.cfg.max_tokens,
            "stream": False,
        }
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
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
        effort = self.cfg.reasoning_effort_overrides.get(stage)
        if not override and not effort:
            return self
        clone = OpenAICompatLLM(self.cfg)
        if effort:
            clone.reasoning_effort = effort.strip()
        if not override:
            return clone
        clone._stage_model = override  # type: ignore[attr-defined]
        orig_model = self.cfg.model

        def _model(o: Optional[str]) -> str:  # noqa: ANN001
            return o or override or orig_model
        clone._model = _model  # type: ignore[method-assign]
        return clone


def build_llm(cfg: LLMConfig) -> BaseLLM:
    return OpenAICompatLLM(cfg)
