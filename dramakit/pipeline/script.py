"""Stage 4 — script: turn each episode's source text into scenes + dialogue."""
from __future__ import annotations

import re
import traceback
import uuid

from ..models import (Beat, Line, LineKind, Scene, Shot, ShotType, Status,
                      is_narration)
from ..prompts import templates as T
from ..utils.text import estimate_reading_seconds
from .base import Context, llm_pool, run_jobs, write_workers
# the camera helpers and the repairs the shot list needs - they belong
# to the shot list, and the shot list is written here now
from .storyboard import (_enforce_coverage, _fallback_shots,
                         _repair_characters, _repair_line_casts,
                         _split_long_shots, _strip_facing_camera, _to_angle,
                         _to_height, _to_lens, _to_shot_type)
from .shots import enforce_variety, merge_duplicate_shots, strip_connector


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
    """The kind of a line, from the several names the model may use."""
    s = str(v or "").strip().lower()
    if s in ("voice_over", "vo", "inner", "monologue", "inner_voice",
             "thought", "voiceover"):
        return LineKind.MONOLOGUE
    if s in ("off_screen", "os", "offscreen", "off_screen_voice"):
        return LineKind.OFF_SCREEN
    if s in ("narration", "narrator"):
        return LineKind.NARRATION
    if s in ("caption", "subtitle"):
        return LineKind.CAPTION
    try:
        return LineKind(s)
    except ValueError:
        return LineKind.DIALOGUE


def _parse_scenes(data) -> list:
    """The model's answer, as scenes and lines and beats.

    The beats are the visible moments of the scene, in order, with the
    lines that happen in them.  A beat whose numbers do not fit the
    scene's lines keeps its action and loses the numbers - a picture
    filmed wrongly is better than a picture dropped.
    """
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
        n_lines = len(sc.lines)
        for b in (s.get("beats") or []):
            action = (b.get("action") or "").strip()
            if not action:
                continue
            idx = []
            for v in (b.get("lines") or []):
                try:
                    n = int(v)
                except (TypeError, ValueError):
                    continue
                if 1 <= n <= n_lines and n not in idx:
                    idx.append(n)
            sc.beats.append(Beat(action=action, lines=idx))
        if sc.lines:
            scenes.append(sc)
    return scenes


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


# "接上：" is a note to the reader, not to the camera.  It says the shot
# continues the one before it, which is true of every shot in a scene
# and means nothing to the model that has to draw it.


def _parse_slug(slug: str) -> tuple[str, str]:
    """The scene heading: 内/外 · 地点 · 时间.

    The place may carry a sub-area with a dot in it ("藤萝峰青萝居·内室"),
    so the heading is split on the spaced dot and the place is whatever
    is in between.
    """
    text = (slug or "").strip()
    if not text:
        return "", "日"
    parts = [p.strip() for p in text.split(" · ")]
    if len(parts) >= 3:
        place = " · ".join(parts[1:-1])
        tod = parts[-1]
    elif len(parts) == 2:
        place, tod = parts[0], parts[1]
    else:
        place, tod = parts[0], "日"
    return place, _time_of_day(tod)


def _time_of_day(text: str) -> str:
    """The four times a scene can be at."""
    t = (text or "").strip()
    if any(w in t for w in ("夜", "晚")):
        return "夜"
    if any(w in t for w in ("晨", "早")):
        return "晨"
    if any(w in t for w in ("昏", "暮", "黄昏")):
        return "昏"
    return "日"


# A shot's action is a paragraph about one picture, and a line is one
# sentence.  A model that writes a page into either of them is not
# writing a shot, and the text goes into every prompt downstream - so
# there is a limit, and going over it is said out loud.
_MAX_ACTION = 2000
_MAX_LINE = 200


def _clip(text: str, limit: int) -> str:
    t = (text or "").strip()
    return t if len(t) <= limit else t[:limit].rstrip() + "…"


def _parse_shots(raw_shots, scene, dmin: float, dmax: float) -> list:
    """The model's shots, as shots."""
    out = []
    for i, s in enumerate(raw_shots or []):
        if not isinstance(s, dict):
            continue
        idx: list[int] = []
        for v in (s.get("lines") or []):
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            if n > 0 and n not in idx:
                idx.append(n)
        covered: list[int] = []
        for v in (s.get("beats") or []):
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            if 0 < n <= len(getattr(scene, "beats", []) or []) and n not in covered:
                covered.append(n)
        out.append(Shot(
            id=_id("sh"), index=i,
            shot_type=_to_shot_type(s.get("shot_type", "中景")),
            camera_move=s.get("camera_move", "固定"),
            angle=_to_angle(s.get("angle", "")),
            height=_to_height(s.get("height", "")),
            lens=_to_lens(s.get("lens", "")),
            purpose=(s.get("purpose") or "").strip(),
            subject=(s.get("subject") or "").strip(),
            duration=_clamp(s.get("duration"), dmin, dmax, 3.0),
            action=strip_connector(_strip_facing_camera(
                _clip(s.get("action", ""), _MAX_ACTION))),
            characters=[str(c) for c in (s.get("characters") or [])],
            line_indices=sorted(idx),
            beats=sorted(covered),
        ))
    return out


def _clamp(value, lo: float, hi: float, default: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


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
    # the card for this project's genre: the craft of this kind of story,
    # and it is one card - the main genre
    rules += loader.genre_rules(ctx, "script")
    # the director's rules ride along: the coverage, the axis, the frame
    from ..skills.film import DIRECTOR_RULES
    rules += DIRECTOR_RULES
    dmin, dmax = (float(cfg.storyboard.shot_duration_range[0]),
                  float(cfg.storyboard.shot_duration_range[-1]))
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
        jobs.append((ep, block, seconds, budget_chars, budget_lines))

    # The episodes are independent of each other, and the endpoint answers
    # several calls at once - so they are asked together.
    def _one(job):
        ep, block, seconds, budget_chars, budget_lines = job
        try:
            return _write_episode(job)
        except Exception:  # noqa: BLE001
            # a failure with no traceback is a failure nobody can find
            ctx.log.error("script: 第%d集写的时候出了事：\n%s",
                          ep.index, traceback.format_exc())
            raise

    def _write_episode(job):
        ep, block, seconds, budget_chars, budget_lines = job
        # 1. the shape of the episode: the scenes, and the beats in them
        plan = pool.next().complete_json(
            T.SCRIPT_PLAN_SYSTEM,
            T.render(T.SCRIPT_PLAN_USER, genre=genre,
                     min_scenes=2, max_scenes=8,
                     screenwriter_rules=rules,
                     character_names=char_names, location_names=loc_names,
                     text=block[:12000]))
        if isinstance(plan, list):
            plan = plan[0] if plan else {}
        scenes: list = []
        for si, s in enumerate(plan.get("scenes", []) or [], 1):
            place, tod = _parse_slug(s.get("slug", ""))
            sc = Scene(id=_id("sc"), index=si, location=place,
                       time_of_day=tod,
                       summary=_clip(s.get("action") or "", _MAX_ACTION),
                       mood=s.get("mood", "中性"),
                       bgm_mood=s.get("bgm_mood", ""))
            for b in (s.get("beats") or []):
                action = _clip(b.get("action") or "", _MAX_ACTION)
                if action:
                    sc.beats.append(Beat(action=action))
            if sc.beats:
                scenes.append(sc)

        # 2. each scene whole: the lines and the shots that cover them
        for sc in scenes:
            beats_text = "\n".join("- %d. %s" % (i, b.action)
                                   for i, b in enumerate(sc.beats, 1))
            # How long this scene is on screen, and how many shots that
            # takes.  The beats are the floor - each one is a picture of
            # its own - and the seconds are the other end: a scene that
            # has a hundred seconds of screen time needs more than the
            # three or four things that happen in it.
            scene_seconds = int(round(seconds / max(1, len(scenes))))
            want = max(cfg.storyboard.min_shots_per_scene, len(sc.beats),
                       int(round(scene_seconds / 10.0)))
            want = min(want, cfg.storyboard.max_shots_per_scene)
            scene_avg = round(scene_seconds / max(1, want), 1)
            data = pool.next().complete_json(
                T.SCRIPT_SCENE_SYSTEM,
                T.render(T.SCRIPT_SCENE_USER,
                         ep_index=ep.index, ep_total=len(ctx.target_episodes()),
                         genre=genre,
                         location=sc.location or "场景", time_of_day=sc.time_of_day,
                         mood=sc.mood, summary=sc.summary or "",
                         action=sc.summary or "",
                         beats_text=beats_text or "（这一场没有拍点）",
                         text=block[:12000],
                         character_anchors=_char_anchors(ctx, sc),
                         screenwriter_rules=rules,
                         scene_seconds=scene_seconds,
                         scene_shots=want,
                         scene_avg=scene_avg,
                         dur_min=dmin, dur_max=dmax,
                         budget_seconds=int(seconds), budget_chars=budget_chars,
                         budget_lines=budget_lines))
            if isinstance(data, list):
                data = data[0] if data else {}
            for li, l in enumerate(data.get("lines", []) or [], 1):
                txt = _clip(_strip_direction(l.get("text") or ""), _MAX_LINE)
                if not txt:
                    continue
                emotion = (l.get("emotion") or "平静").strip()
                for note in _DIRECTION.findall(l.get("text") or ""):
                    note = note.strip("（）() ")
                    if note and note not in emotion:
                        emotion = (emotion + "，" + note) if emotion != "平静" else note
                sc.lines.append(Line(id=_id("ln"), kind=_to_kind(l.get("kind", "dialogue")),
                                     speaker=(l.get("speaker") or "旁白").strip(),
                                     text=txt, emotion=emotion))
            sc.shots = _parse_shots(data.get("shots", []), sc, dmin, dmax)
            if not sc.shots:
                sc.shots = _fallback_shots(sc, dmin, dmax)
            _repair_line_casts(sc)
            _repair_characters(ctx, sc)
            # two shots that are the same picture are one shot: the model
            # copies the shot before it when it wants a new line to have
            # its own moment, and a cut to the same picture is not a cut
            merged = merge_duplicate_shots(sc)
            if merged:
                ctx.log.info("script: 第%d集《%s》%s 合并了 %d 个重复镜头",
                             ep.index, sc.location, sc.time_of_day, merged)
            longest = max((len(sh.action or "") for sh in sc.shots),
                          default=0)
            ctx.log.info("script: 第%d集《%s》%s %s：%d 镜，最长的画面描述 %d 字，"
                         "台词 %d 句",
                         ep.index, sc.location, sc.time_of_day, sc.id[:6],
                         len(sc.shots), longest, len(sc.lines))
            _split_long_shots(sc)
            _enforce_coverage(sc)
            # the framings have to differ: a scene that is one angle in
            # one size, over and over, is the most amateur-looking
            # picture there is.  Last in the chain, so that the shots
            # the other repairs added are counted too.
            varied = enforce_variety(sc)
            if varied:
                ctx.log.info("script: 第%d集《%s》%s 改了 %d 处的景别/角度",
                             ep.index, sc.location, sc.time_of_day, varied)
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
        n_shots = sum(len(s.shots) for s in ep.scenes)
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 镜",
                     ep.index, ep.title, len(ep.scenes), n_shots)
        # the dialogue check: a script that is one long interrogation
        # reads like a form being filled in
        pairs, lines = _flatness(ep.scenes)
        pct = int(pairs * 100 / max(1, lines))
        if pct >= 25:
            ctx.log.warning("script: 第%d集有 %d%% 的台词是一问一答，"
                            "人物像在填表而不是在说话", ep.index, pct)
    return {"episodes_scripted": done}


def _char_anchors(ctx: Context, sc: Scene) -> str:
    """The character sheets of the people in this scene."""
    names = set()
    for sh in getattr(sc, "shots", []) or []:
        names.update(sh.characters or [])
    out = []
    for c in ctx.project.characters:
        if names and c.name not in names:
            continue
        desc = c.visual_prompt or c.anchor_prompt or c.appearance or ""
        if desc:
            out.append("%s：%s" % (c.name, desc))
    return "\n".join(out) or "（这一场没有人物参考图）"
