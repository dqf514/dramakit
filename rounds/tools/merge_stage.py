"""The screenplay and the shots, written in one breath.

They were two stages: the writer made a script, and the director read
it and made a shot list.  That is how a film is made - but a film's
script is written for people to act, and here it is written for a model
to draw.  Between the two there was a translation, and a translation
loses things: the novel's pictures were dropped on the way.

Now they are one stage.  Two calls, and the scene is written whole:

  one call per episode - the shape of the episode and the beats of
  each scene (the visible moments the novel has);
  one call per scene - its lines and the shots that cover them, in the
  same breath, so the coverage is designed for the words.

The number of calls is the same as before.  What is gone is the room
in the middle: nothing is written twice, and nothing is summarised on
the way from the book to the frame.
"""
import pathlib

ROOT = pathlib.Path(r"E:\dramakit")
P = ROOT / "dramakit" / "pipeline" / "script.py"
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

# the imports: the shot helpers come from the director's side
old_imports = """from ..models import Beat, Line, LineKind, Scene, Status
from ..prompts import templates as T
from .base import Context, llm_pool, run_jobs, write_workers"""
new_imports = """from ..models import Beat, Line, LineKind, Scene, Shot, ShotType, Status
from ..prompts import templates as T
from .base import Context, llm_pool, run_jobs, write_workers
# the camera helpers and the repairs the shot list needs - they belong
# to the shot list, and the shot list is written here now
from .storyboard import (_enforce_coverage, _repair_characters,
                         _repair_line_casts, _split_long_shots,
                         _strip_facing_camera, _to_angle, _to_height,
                         _to_lens, _to_shot_type)"""
assert old_imports in text
text = text.replace(old_imports, new_imports, 1)

# the stage itself
start = text.index("def run(ctx: Context) -> dict:")
end = text.index("def _flatness(scenes: list)")
new_run = '''def _parse_shots(raw_shots, scene, dmin: float, dmax: float) -> list:
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
            action=_strip_facing_camera(s.get("action", "")),
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
    rules += loader.genre_rules(ctx)
    # the director's rules ride along: the coverage, the axis, the frame
    from .storyboard import DIRECTOR_RULES
    rules += DIRECTOR_RULES
    dmin, dmax = (float(cfg.storyboard.shot_duration_range[0]),
                  float(cfg.storyboard.shot_duration_range[-1]))
    done = 0
    jobs: list = []
    for ep in ctx.target_episodes():
        ctx.check_stop()   # 一集一问：停止能在下一集生效
        if ctx.stage_done(ep, "script") and ep.scenes:
            continue
        block = ctx.store.abs(ep.source_path).read_text(encoding="utf-8") \\
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
            sc = Scene(id=_id("sc"), index=si, location=s.get("location", ""),
                       time_of_day=s.get("time_of_day", "日"),
                       summary=s.get("summary", ""), mood=s.get("mood", "中性"),
                       bgm_mood=s.get("bgm_mood", ""))
            for b in (s.get("beats") or []):
                action = (b.get("action") or "").strip()
                if action:
                    sc.beats.append(Beat(action=action))
            if sc.beats:
                scenes.append(sc)

        # 2. each scene whole: the lines and the shots that cover them
        for sc in scenes:
            beats_text = "\\n".join("- %d. %s" % (i, b.action)
                                   for i, b in enumerate(sc.beats, 1))
            spoken = [l for l in sc.lines if not is_narration(l)]
            secs = sum(estimate_reading_seconds(l.text) for l in spoken) * 1.2
            want = max(cfg.storyboard.min_shots_per_scene,
                       (int(secs * 100) + 349) // 350)
            want = max(want, len(sc.beats))
            want = min(want, cfg.storyboard.max_shots_per_scene)
            scene_seconds = int(round(seconds / max(1, len(scenes))))
            data = pool.next().complete_json(
                T.SCRIPT_SCENE_SYSTEM,
                T.render(T.SCRIPT_SCENE_USER,
                         ep_index=ep.index, ep_total=len(ctx.target_episodes()),
                         location=sc.location or "场景", time_of_day=sc.time_of_day,
                         mood=sc.mood, summary=sc.summary or "",
                         beats_text=beats_text or "（这一场没有拍点）",
                         text=block[:12000],
                         character_anchors=_char_anchors(ctx, sc),
                         screenwriter_rules=rules,
                         scene_seconds=scene_seconds,
                         scene_shots=want,
                         budget_seconds=int(seconds), budget_chars=budget_chars,
                         budget_lines=budget_lines))
            if isinstance(data, list):
                data = data[0] if data else {}
            for li, l in enumerate(data.get("lines", []) or [], 1):
                txt = _strip_direction(l.get("text") or "")
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
            _split_long_shots(sc)
            _enforce_coverage(sc)
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
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 镜",
                     ep.index, ep.title, len(ep.scenes),
                     sum(len(s.shots) for s in ep.scenes))
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
    return "\\n".join(out) or "（这一场没有人物参考图）"


'''
text = text[:start] + new_run + text[end:]

if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("合并后的阶段写好了")
