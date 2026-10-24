"""The AI brain: resolves a model per task role.

Models are configured as a registry (Config.models):
  * entry order  — priority order (the first entry claiming a role wins)
  * roles        — which tasks each model handles
  * default      — catches every task nobody claimed

If the registry is empty, the legacy `llm` config is used unchanged and
`ai.light_*` (when configured) keeps handling tagging.

Every method degrades gracefully: if no LLM is reachable the callers get an
empty/None result plus a logged warning rather than an exception, so the web
console and CLI stay usable while the user is still setting things up.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..config import AIConfig, Config, LLMConfig
from ..providers.base import BaseLLM
from ..providers.llm import OpenAICompatLLM

log = logging.getLogger("dramakit.ai")


class Brain:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.ai: AIConfig = cfg.ai
        self._clients: dict[tuple[str, bool], BaseLLM] = {}
        self._ok: dict[tuple[str, bool], tuple[bool, str]] = {}

    # ---------------------------------------------------------------- models
    def model_cfg(self, role: str = "") -> LLMConfig:
        return self.cfg.resolve_llm(role)

    def llm(self, role: str = "", *, fast: bool = False) -> BaseLLM:
        key = (role, fast)
        if key not in self._clients:
            conf = self.model_cfg(role)
            if fast:
                # Interactive/UI calls must fail fast: no retry backoff and a
                # capped timeout so a dead endpoint degrades quickly (every
                # Brain caller has a graceful fallback). Heavy pipeline work
                # uses Providers.llm_for(), not this.
                conf = conf.model_copy(update={
                    "max_retries": 0,
                    "timeout": min(conf.timeout, self.ai.main_timeout),
                })
            self._clients[key] = OpenAICompatLLM(conf)
        return self._clients[key]

    def _task_temp(self, fallback: float) -> Optional[float]:
        # With an explicit registry each model's own temperature wins; legacy
        # single-model configs keep the task-tuned values.
        return None if self.cfg.models.entries else fallback

    # ---------------------------------------------------------------- health
    def probe(self) -> dict:
        """Cheap liveness check of the default and tagging models."""
        def _ok(role: str) -> tuple[bool, str]:
            key = (role, True)
            if key not in self._ok:
                try:
                    r = self.llm(role, fast=True).complete(
                        "You are a health probe.", "Reply with: OK", max_tokens=5)
                    self._ok[key] = (True, (r.text or "").strip()[:20])
                except Exception as e:  # noqa: BLE001
                    self._ok[key] = (False, str(e)[:120])
            return self._ok[key]

        main_ok, main_msg = _ok("")
        light_ok, light_msg = _ok("tag")
        main_cfg = self.model_cfg("")
        tag_cfg = self.model_cfg("tag")
        roles = []
        for e in self.cfg.models.entries:
            for r in e.roles:
                if r not in roles:
                    roles.append(r)
        return {
            "main": {"model": main_cfg.model, "ok": main_ok, "detail": main_msg},
            "light": {"model": tag_cfg.model, "ok": light_ok, "detail": light_msg,
                      "aliased": tag_cfg == main_cfg},
            "default": main_cfg.model,
            "roles": {r: self.model_cfg(r).model for r in roles},
        }

    # ---------------------------------------------------------------- core
    def chat(self, system: str, user: str, *, role: str = "chat",
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> Optional[str]:
        llm = self.llm(role, fast=True)
        try:
            r = llm.complete(system, user, temperature=temperature,
                             max_tokens=max_tokens)
            return r.text
        except Exception as e:  # noqa: BLE001
            log.warning("brain.chat(%s) failed: %s", role, str(e)[:200])
            return None

    def json(self, system: str, user: str, *, role: str = "chat",
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> Optional[dict | list]:
        llm = self.llm(role, fast=True)
        try:
            return llm.complete_json(system, user, temperature=temperature,
                                     max_tokens=max_tokens)
        except Exception as e:  # noqa: BLE001
            log.warning("brain.json(%s) failed: %s", role, str(e)[:200])
            return None

    # ---------------------------------------------------------------- tagging
    def tag(self, text: str, *, kinds: Optional[list[str]] = None,
            extra_hint: str = "") -> dict:
        """Classify a chunk of text into the configured tag taxonomies.

        Returns {"tags": [...], "category": "...", "summary": "..."} using only
        vocabulary from ai.tag_taxonomies so categories stay consistent.
        """
        tax = self.ai.tag_taxonomies or {}
        use_kinds = kinds or list(tax.keys())
        vocab = {k: tax.get(k, []) for k in use_kinds if tax.get(k)}
        sys = (
            "你是短剧资产打标引擎。只输出 JSON。根据给定文本，从每个维度的候选词里"
            "挑选最贴切的标签；候选词之外不要自造，除非文本明显需要（可少量补充）。"
            f"输出格式: {{\"tags\": [\"...\"], \"category\": \"...\", \"summary\": \"一句话\"}}"
            f"。tags 不超过 {self.ai.tag_max} 个。语言: {self.ai.language}。"
        )
        user_msg = f"维度候选词:\n{vocab}\n\n额外提示: {extra_hint or '无'}\n\n文本:\n{text[:2000]}"
        out = self.json(sys, user_msg, role="tag",
                        temperature=self._task_temp(self.ai.light_temperature))
        if not isinstance(out, dict):
            return {"tags": [], "category": "", "summary": ""}
        tags = [str(t).strip() for t in (out.get("tags") or []) if str(t).strip()]
        return {
            "tags": tags[: self.ai.tag_max],
            "category": str(out.get("category", "")).strip(),
            "summary": str(out.get("summary", "")).strip(),
        }

    def summarize(self, text: str, *, max_chars: int = 120) -> str:
        s = self.chat("用一句话概括以下内容，只输出概括本身。", text[:3000],
                      role="tag", max_tokens=200)
        return (s or "").strip()[:max_chars]

    # ---------------------------------------------------------------- search
    def expand_query(self, query: str) -> dict:
        """Turn a natural-language search into structured catalog filters.

        Returns {"keywords": [...], "tags": [...], "category": "", "kinds": []}.
        Falls back to naive whitespace/keyword split if the LLM is unavailable.
        """
        tax = self.ai.tag_taxonomies or {}
        sys = (
            "你是检索查询解析器。把用户的自然语言检索意图转成结构化过滤条件，只输出 JSON: "
            "{\"keywords\": [关键词...], \"tags\": [标签...], \"category\": \"资产大类或空\", "
            "\"kinds\": [资产类型...]}。kinds 取自: episode/scene/shot/line/image/video/"
            "audio/subtitle/bgm/cover/project。tags 尽量取自给定词表。"
        )
        user_msg = f"标签词表:\n{tax}\n\n用户检索: {query}"
        out = self.json(sys, user_msg, role="search",
                        temperature=self._task_temp(0.1))
        if not isinstance(out, dict):
            kws = [w for w in query.replace("，", " ").replace(",", " ").split() if w]
            return {"keywords": kws, "tags": [], "category": "", "kinds": []}
        return {
            "keywords": [str(k).strip() for k in (out.get("keywords") or []) if str(k).strip()],
            "tags": [str(t).strip() for t in (out.get("tags") or []) if str(t).strip()],
            "category": str(out.get("category", "")).strip(),
            "kinds": [str(k).strip() for k in (out.get("kinds") or []) if str(k).strip()],
        }
