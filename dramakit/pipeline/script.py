"""Stage 4 — script: turn each episode's source text into scenes + dialogue."""
from __future__ import annotations

import uuid

from ..models import Line, LineKind, Scene, Status
from ..prompts import templates as T
from .base import Context


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _to_kind(v: str) -> LineKind:
    try:
        return LineKind(str(v).lower())
    except ValueError:
        return LineKind.DIALOGUE


def run(ctx: Context) -> dict:
    cfg = ctx.cfg
    llm = ctx.providers.llm_for("script")
    char_names = ", ".join(c.name for c in ctx.project.characters) or "（自行判断）"
    genre = ctx.project.art_direction.genre
    done = 0
    for ep in ctx.target_episodes():
        if ctx.stage_done(ep, "script") and ep.scenes:
            continue
        block = ctx.store.abs(ep.source_path).read_text(encoding="utf-8") \
            if ep.source_path else ""
        if not block.strip():
            ctx.log.warning("script: 第%d集无原文，跳过", ep.index)
            ctx.mark(ep, "script", Status.SKIPPED)
            continue
        # how much the episode may say: Chinese speech runs about 4.5 chars a
        # second, and a short drama loses people if it lingers
        seconds = float(ep.duration_target or cfg.segment.episode_duration)
        budget_chars = int(seconds * 4.5)
        budget_lines = max(4, int(seconds / 4.5))
        user = T.render(T.SCRIPT_USER, genre=genre, min_scenes=2, max_scenes=8,
                        character_names=char_names, text=block[:12000],
                        budget_seconds=int(seconds), budget_chars=budget_chars,
                        budget_lines=budget_lines)
        try:
            data = llm.complete_json(T.SCRIPT_SYSTEM, user)
        except Exception as e:  # noqa: BLE001
            ctx.log.error("script: 第%d集失败 %s", ep.index, e)
            ctx.mark(ep, "script", Status.FAILED)
            if cfg.pipeline.fail_fast:
                raise
            continue
        if isinstance(data, list):
            data = data[0] if data else {}
        scenes = []
        for si, s in enumerate(data.get("scenes", []) or [], 1):
            sc = Scene(id=_id("sc"), index=si, location=s.get("location", ""),
                       time_of_day=s.get("time_of_day", "日"),
                       summary=s.get("summary", ""), mood=s.get("mood", "中性"),
                       bgm_mood=s.get("bgm_mood", ""))
            for li, l in enumerate(s.get("lines", []) or [], 1):
                txt = (l.get("text") or "").strip()
                if not txt:
                    continue
                sc.lines.append(Line(id=_id("ln"), kind=_to_kind(l.get("kind", "dialogue")),
                                     speaker=(l.get("speaker") or "旁白").strip(),
                                     text=txt, emotion=l.get("emotion", "平静")))
            if sc.lines:
                scenes.append(sc)
        ep.scenes = scenes
        ctx.mark(ep, "script", Status.DONE)
        ctx.save()
        done += 1
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 句",
                     ep.index, ep.title, len(scenes), sum(len(s.lines) for s in scenes))
    return {"episodes_scripted": done}
