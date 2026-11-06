"""Stage 4 — script: turn each episode's source text into scenes + dialogue."""
from __future__ import annotations

import re
import uuid

from ..models import Line, LineKind, Scene, Status
from ..prompts import templates as T
from .base import Context, llm_pool, run_jobs, write_workers


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# A note in brackets is a note for the actor: 端着、躲开、攥紧.  The text
# is what the voice says and what the subtitle shows, so a note that
# slipped into it is taken back out.  What is left is what gets said.
_DIRECTION = re.compile(r"[（(][^）)]{0,40}[）)]")


def _strip_direction(text: str) -> str:
    out = _DIRECTION.sub("", text or "")
    return out.strip()


def _to_kind(v: str) -> LineKind:
    try:
        return LineKind(str(v).lower())
    except ValueError:
        return LineKind.DIALOGUE


def _flatness(scenes: list) -> tuple[int, int]:
    """How much of the dialogue is a question answered straight.

    A script that is one long interrogation reads like a form being
    filled in: the questions are answered in one short line, with
    nothing in between - no resistance, no interruption, no lie.  The
    number says how much of the script is that.
    """
    pairs = 0
    lines = 0
    for sc in scenes:
        ls = list(sc.lines)
        lines += len(ls)
        for i, ln in enumerate(ls[:-1]):
            if "？" not in ln.text and "?" not in ln.text:
                continue
            nxt = ls[i + 1]
            if "？" in nxt.text or "?" in nxt.text:
                continue
            if len(nxt.text) <= 12:
                pairs += 1
    return pairs, lines


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
        jobs.append((ep, user, block))

    # The episodes are independent of each other, and the endpoint answers
    # several calls at once - so they are asked together, not one after
    # another.
    def _parse(data) -> list:
        """The model's answer, as scenes and lines."""
        if isinstance(data, list):
            data = data[0] if data else {}
        scenes = []
        for si, s in enumerate(data.get("scenes", []) or [], 1):
            sc = Scene(id=_id("sc"), index=si, location=s.get("location", ""),
                       time_of_day=s.get("time_of_day", "日"),
                       summary=s.get("summary", ""), mood=s.get("mood", "中性"),
                       bgm_mood=s.get("bgm_mood", ""))
            for li, l in enumerate(s.get("lines", []) or [], 1):
                txt = _strip_direction(l.get("text") or "")
                if not txt:
                    continue
                emotion = (l.get("emotion") or "平静").strip()
                # a note that was in the text is not lost: it goes into the
                # emotion field, where the performance notes belong
                for note in _DIRECTION.findall(l.get("text") or ""):
                    note = note.strip("（）() ")
                    if note and note not in emotion:
                        emotion = (emotion + "，" + note) if emotion != "平静" else note
                sc.lines.append(Line(id=_id("ln"), kind=_to_kind(l.get("kind", "dialogue")),
                                     speaker=(l.get("speaker") or "旁白").strip(),
                                     text=txt, emotion=emotion))
            if sc.lines:
                scenes.append(sc)
        return scenes

    def _draft_text(scenes: list) -> str:
        """The scenes as the editor will see them."""
        out = []
        for sc in scenes:
            out.append("【%s / %s】%s" % (sc.location, sc.time_of_day, sc.summary))
            for ln in sc.lines:
                out.append("  %s：%s" % (ln.speaker, ln.text))
        return "\n".join(out)

    def _one(job):
        ep, user, block = job
        data = pool.next().complete_json(T.SCRIPT_SYSTEM, user)
        scenes = _parse(data)
        # The editor. The same scenes, the same speakers, the same
        # information - and every line with somebody's fingerprints on it.
        # A draft that cannot be polished is kept as it is: a second
        # failure must not cost the first one.
        if scenes and getattr(cfg.segment, "polish_dialogue", True):
            try:
                pol = pool.next().complete_json(
                    T.SCRIPT_POLISH_SYSTEM,
                    T.render(T.SCRIPT_POLISH_USER, text=block[:8000],
                             draft=_draft_text(scenes)))
                polished = _parse(pol)
                if polished:
                    scenes = polished
                    ctx.log.info("script: 第%d集台词已打磨", ep.index)
                else:
                    ctx.log.warning("script: 第%d集打磨没有结果，保留初稿", ep.index)
            except Exception as e:  # noqa: BLE001
                ctx.log.warning("script: 第%d集打磨失败(%s)，保留初稿",
                                ep.index, str(e)[:120])
        # the episode is written and saved here, not after the whole
        # batch: a run that is stopped halfway keeps the episodes that
        # were already done
        ep.scenes = scenes
        ctx.mark(ep, "script", Status.DONE)
        ctx.save()
        return len(scenes)

    results = run_jobs(ctx, jobs, _one, workers=write_workers(ctx),
                       label="script")
    for (job, _scenes, err) in results:
        ep = job[0]
        if err:
            ctx.log.error("script: 第%d集失败 %s", ep.index, err)
            ctx.mark(ep, "script", Status.FAILED)
            if cfg.pipeline.fail_fast:
                raise RuntimeError(err)
            continue
        done += 1
        pairs, lines = _flatness(ep.scenes)
        pct = int(pairs * 100 / max(1, lines))
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 句（其中 %d 处一问一答，%d%%）",
                     ep.index, ep.title, len(ep.scenes), lines, pairs, pct)
        if pct >= 25:
            ctx.log.warning("script: 第%d集有 %d%% 的台词是一问一答，"
                            "人物像在填表而不是在说话", ep.index, pct)
    return {"episodes_scripted": done}
