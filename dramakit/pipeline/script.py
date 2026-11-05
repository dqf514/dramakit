"""Stage 4 — script: turn each episode's source text into scenes + dialogue."""
from __future__ import annotations

import uuid

from ..models import Line, LineKind, Scene, Status
from ..prompts import templates as T
from .base import Context, llm_pool, run_jobs, write_workers


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _to_kind(v: str) -> LineKind:
    try:
        return LineKind(str(v).lower())
    except ValueError:
        return LineKind.DIALOGUE


def run(ctx: Context) -> dict:
    cfg = ctx.cfg
    pool = llm_pool(ctx, "script")
    char_names = ", ".join(c.name for c in ctx.project.characters) or "（自行判断）"
    loc_names = ", ".join(l.name for l in ctx.project.locations) or "（自行判断）"
    genre = ctx.project.art_direction.genre
    from ..skills import loader
    from ..skills.film import SCREENWRITER_RULES
    # the rules are the same for every episode, so they are read once
    rules = SCREENWRITER_RULES + loader.for_stage(ctx, "script")
    done = 0
    jobs: list = []
    for ep in ctx.target_episodes():
        ctx.check_stop()   # 一集一问：停止能在下一集生效
        if ctx.stage_done(ep, "script") and ep.scenes:
            continue
        block = ctx.store.abs(ep.source_path).read_text(encoding="utf-8") \
            if ep.source_path else ""
        if not block.strip():
            ctx.log.warning("script: 第%d集无原文，跳过", ep.index)
            ctx.mark(ep, "script", Status.SKIPPED)
            continue
        # how much the episode may say: Chinese speech runs about 4.5 chars a
        # second, and a short drama loses people if it lingers. A short drama
        # episode is a minute, so the source length does not get to decide.
        seconds = float(ep.duration_target or cfg.segment.episode_duration)
        seconds = min(seconds, cfg.segment.max_episode_seconds or seconds)
        budget_chars = int(seconds * 4.5)
        budget_lines = max(4, int(seconds / 4.5))
        user = T.render(T.SCRIPT_USER, genre=genre, min_scenes=2, max_scenes=8,
                        screenwriter_rules=rules,
                        character_names=char_names, location_names=loc_names,
                        text=block[:12000],
                        budget_seconds=int(seconds), budget_chars=budget_chars,
                        budget_lines=budget_lines)
        jobs.append((ep, user))

    # The episodes are independent of each other, and the endpoint answers
    # several calls at once - so they are asked together, not one after
    # another.
    def _one(job):
        ep, user = job
        data = pool.next().complete_json(T.SCRIPT_SYSTEM, user)
        if isinstance(data, list):
            data = data[0] if data else {}
        return data

    results = run_jobs(ctx, jobs, _one, workers=write_workers(ctx),
                       label="script")
    for (job, data, err) in results:
        ep, _user = job
        if err:
            ctx.log.error("script: 第%d集失败 %s", ep.index, err)
            ctx.mark(ep, "script", Status.FAILED)
            if cfg.pipeline.fail_fast:
                raise RuntimeError(err)
            continue
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
