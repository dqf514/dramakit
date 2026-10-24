"""Stage 3 — segment: split the story into episodes with titles and hooks.

Episode count strategies:
  fixed_count     exactly cfg.episode_count episodes
  fixed_duration  total reading time / episode_duration
  by_chapter      one episode per chapter (or per cfg.episode_count chapters)
  auto            by duration, but snapped to chapter boundaries when possible

Text is cut deterministically at sentence/paragraph boundaries (cheap, reliable);
the LLM only writes each episode's title / logline / hook / recap.
"""
from __future__ import annotations

import json
import math

from ..models import Episode, Status
from ..prompts import templates as T
from ..utils.text import chunk_by_chars, estimate_reading_seconds
from .base import Context

CHARS_PER_SEC = 4.2


def _episode_count(total_chars: float, cfg, n_chapters: int) -> int:
    if cfg.strategy == "fixed_count" and cfg.episode_count > 0:
        return cfg.episode_count
    if cfg.strategy == "by_chapter" and n_chapters > 0:
        return max(1, n_chapters)
    total_sec = total_chars / CHARS_PER_SEC
    n = max(1, round(total_sec / max(cfg.episode_duration, 10)))
    # clamp to sane range
    n = max(1, min(n, 500))
    return n


def _split_blocks(text: str, chapters: list[dict], n: int, cfg) -> list[str]:
    if cfg.respect_chapters and chapters and len(chapters) >= n:
        # group chapters into n buckets as evenly as possible
        per = len(chapters) / n
        blocks = []
        for i in range(n):
            lo = int(round(i * per))
            hi = int(round((i + 1) * per))
            hi = max(hi, lo + 1)
            body = "\n\n".join(c["body"] for c in chapters[lo:hi])
            if body.strip():
                blocks.append(body)
        if blocks:
            return blocks
    # char-based split at sentence boundaries
    target = max(200, int(len(text) / max(n, 1)))
    if cfg.max_chars_per_episode > 0:
        target = cfg.max_chars_per_episode
    return chunk_by_chars(text, target)


def run(ctx: Context) -> dict:
    cfg = ctx.cfg.segment
    if ctx.project.episodes and ctx.project.stage_status.get("segment") == "done":
        ctx.log.info("segment: 已完成，%d 集", len(ctx.project.episodes))
        return {"skipped": True}

    text = ctx.store.cleaned_text_path().read_text(encoding="utf-8")
    chapters = json.loads(ctx.store.chapters_path().read_text(encoding="utf-8")) \
        if ctx.store.chapters_path().exists() else []

    n = _episode_count(len(text), cfg, len(chapters))
    blocks = _split_blocks(text, chapters, n, cfg)
    total = len(blocks)
    ctx.log.info("segment: 切成 %d 集（策略=%s）", total, cfg.strategy)

    llm = ctx.providers.llm_for("segment")
    episodes: list[Episode] = []
    for i, block in enumerate(blocks, 1):
        # persist the block so script stage can read it back
        ctx.store.episode_source_path(i).write_text(block, encoding="utf-8")
        ep = Episode(
            id=f"ep{i:03d}", index=i, duration_target=cfg.episode_duration,
            source_path=ctx.store.rel(ctx.store.episode_source_path(i)),
        )
        # LLM packaging (title/logline/hook) — tolerant of failures
        try:
            dur = estimate_reading_seconds(block, CHARS_PER_SEC)
            extra = "本集为开场，需冷开场直接抛冲突。" if (i == 1 and cfg.cold_open) else ""
            user = T.render(T.SEGMENT_USER, title=ctx.project.meta.title or "本剧",
                            ep_index=i, ep_total=total, duration=int(dur),
                            hook_style=cfg.hook_style, extra_hint=extra, text=block[:6000])
            data = llm.complete_json(T.SEGMENT_SYSTEM, user)
            if isinstance(data, list):
                data = data[0] if data else {}
            ep.title = data.get("title") or f"第{i}集"
            ep.logline = data.get("logline", "")
            ep.hook = data.get("hook", "")
            ep.recap = data.get("recap", "") if cfg.opening_recap else ""
            ep.key_beats = data.get("key_beats", []) or []
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("segment: 第%d集打包失败(%s)，用占位标题", i, e)
            ep.title = f"第{i}集"
        ep.duration_target = round(estimate_reading_seconds(block, CHARS_PER_SEC), 1) \
            or cfg.episode_duration
        episodes.append(ep)

    ctx.project.episodes = episodes
    ctx.project.stage_status["segment"] = "done"
    ctx.save()
    return {"episodes": total}
