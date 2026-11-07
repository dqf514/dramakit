"""Stage 5 — storyboard: design the shot list for every scene."""
from __future__ import annotations

import re
import uuid

from ..models import Shot, ShotType, Status, is_narration
from ..prompts import templates as T
from ..utils.text import estimate_reading_seconds
from . import frame as _frame
from .base import Context, llm_pool, run_jobs, write_workers


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _to_shot_type(v: str) -> ShotType:
    v = (v or "").strip()
    for st in ShotType:
        if st.value == v or st.name.lower() == v.lower():
            return st
    return ShotType.MEDIUM


# --------------------------------------------------------------------------- #
# The three camera choices that are not the size.
#
# A shot's size says how much of the frame the person takes.  It does not
# say whether the person is looking at the lens or at the other person -
# and that is the difference between a drama and a series of interviews.
# So the angle, the height and the lens are three separate answers, and
# the model has to give all three.
# --------------------------------------------------------------------------- #
ANGLES = ("正面", "斜侧", "正侧", "后斜侧", "背面")
HEIGHTS = ("地平", "低", "平视", "高", "顶视")
LENSES = ("广", "标准", "长")

_ANGLE_WORDS = {
    "正面": "正面", "正": "正面", "frontal": "正面", "front": "正面",
    "斜侧": "斜侧", "四分之三": "斜侧", "3/4": "斜侧", "three quarter": "斜侧",
    "正侧": "正侧", "侧面": "正侧", "side": "正侧", "profile": "正侧",
    "后斜侧": "后斜侧", "过肩": "后斜侧", "over shoulder": "后斜侧",
    "背面": "背面", "back": "背面",
}
_HEIGHT_WORDS = {
    "地平": "地平", "地面": "地平",
    "低": "低", "仰": "低", "仰拍": "低", "low": "低",
    "平视": "平视", "平": "平视", "eye level": "平视",
    "高": "高", "俯": "高", "俯拍": "高", "high": "高",
    "顶视": "顶视", "顶": "顶视", "overhead": "顶视",
}
_LENS_WORDS = {
    "广": "广", "广角": "广", "wide": "广",
    "标准": "标准", "标准镜头": "标准", "normal": "标准",
    "长": "长", "长焦": "长", "telephoto": "长", "long": "长",
}


def _to_choice(value, words: dict, table: tuple, default: str) -> str:
    """One of the words of the table, whatever the model wrote."""
    v = (value or "").strip()
    if not v:
        return default
    if v in table:
        return v
    low = v.lower()
    if low in words:
        return words[low]
    for key, item in words.items():
        if key in low:
            return item
    return default


def _to_angle(v: str) -> str:
    return _to_choice(v, _ANGLE_WORDS, ANGLES, "斜侧")


def _to_height(v: str) -> str:
    return _to_choice(v, _HEIGHT_WORDS, HEIGHTS, "平视")


def _to_lens(v: str) -> str:
    return _to_choice(v, _LENS_WORDS, LENSES, "标准")


# "she looks into the lens" - the action text is what the picture is made
# from, and one stray phrase there turns the whole drama into interviews.
_FACING_LENS = ("直视镜头", "看向镜头", "望向镜头", "看镜头", "对着镜头",
                "面对镜头", "面向镜头", "朝着镜头", "冲着镜头", "看向镜头外")


def _strip_facing_camera(action: str) -> str:
    """Take out the words that point a face at the lens.

    What is left is where the person is actually looking, which is
    almost always somebody else.
    """
    text = action or ""
    for phrase in _FACING_LENS:
        if phrase in text:
            text = text.replace(phrase, "看向画外")
    return text.strip()


def _clamp(v, lo: float, hi: float, default: float) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default



def _ref_rhythm_args(profile: dict) -> dict:
    """The numbers of a reference film's rhythm, for the storyboard."""
    if not profile or not profile.get("shots"):
        return {"ref_rhythm": False}
    return {
        "ref_rhythm": True,
        "ref_avg": profile.get("avg_shot", 3.0),
        "ref_median": profile.get("median_shot", 3.0),
        "ref_max": profile.get("max_shot", 5.0),
        "ref_open": profile.get("opening_shot", 2.0),
        "ref_cpm": profile.get("cuts_per_min", 24),
    }


# A cut inside a segment is written as a timestamp: "0.0-2.5秒：…；
# 2.5-5秒：…".  One timestamp is one take; more than one is a cut.
_TIME_CODE = re.compile(r"\d+(?:\.\d+)?\s*[-~至到]\s*\d+(?:\.\d+)?\s*秒")


def _cuts(action: str) -> int:
    """How many camera setups this segment has."""
    return len(_TIME_CODE.findall(action or ""))


def _beat_coverage(sc) -> tuple[int, int]:
    """(the beats that were filmed, the beats there are)."""
    beats = list(getattr(sc, "beats", []) or [])
    if not beats:
        return (0, 0)
    filmed = set()
    for sh in sc.shots:
        for b in (sh.beats or []):
            filmed.add(int(b))
    return (len(filmed), len(beats))


def run(ctx: Context) -> dict:
    cfg = ctx.cfg.storyboard
    pool = llm_pool(ctx, "storyboard")
    char_names = ", ".join(c.name for c in ctx.project.characters) or "（自行判断）"
    dmin, dmax = (cfg.shot_duration_range + [2.0, 5.0])[:2]
    done = 0
    from ..skills import loader as _loader
    from ..skills.film import DIRECTOR_RULES
    _rules = DIRECTOR_RULES + _loader.for_stage(ctx, "storyboard")
    frame = _frame.prompt_frame(ctx)
    system = T.render(T.STORYBOARD_SYSTEM, **frame)
    prefer = "多用运动镜头增强节奏" if cfg.prefer_dynamic else "以固定镜头为主"
    jobs: list = []
    eps_done: list = []
    for ep in ctx.target_episodes():
        ctx.check_stop()   # 一集一问：停止能在下一集生效
        if ctx.stage_done(ep, "storyboard"):
            continue
        if not ep.scenes:
            ctx.log.warning("storyboard: 第%d集无剧本，跳过（先跑 script）", ep.index)
            continue
        # every scene gets the shots its own dialogue needs: a shot holds
        # three and a half seconds of talking, so the count comes from the
        # length of the lines and not from how many there are
        needs = []
        for sc in ep.scenes:
            spoken = [l for l in sc.lines if not is_narration(l)]
            secs = sum(estimate_reading_seconds(l.text) for l in spoken) * 1.2
            want = max(cfg.min_shots_per_scene, (int(secs * 100) + 349) // 350)
            # The beats are the novel's visible moments, and each one is a
            # shot of its own: an empty room, a hand on a switch, the face
            # in the mirror.  A scene that is mostly seen needs more shots
            # than a scene that is mostly said.
            beats = len(getattr(sc, "beats", []) or [])
            if beats:
                want = max(want, beats)
            needs.append(want)
        dialogue_need = sum(needs)
        # How many segments the episode wants is the director's business.
        # The dialogue says how many it needs to hold the lines; the format
        # says roughly how long the episode should be; the model says how
        # long a segment may be.  The director is told all three and the
        # number of segments is not worked out for them.
        avg = (dmin + dmax) / 2.0
        spec = float(ctx.cfg.segment.episode_duration)
        length_need = max(1, int(round(spec / avg)))
        cap = max(cfg.min_shots_per_scene * len(ep.scenes),
                  int(dialogue_need * 2.5))
        total_need = min(max(dialogue_need, length_need), cap)
        target = min(spec, total_need * dmax)
        episode_seconds = int(spec)
        for sc, need in zip(ep.scenes, needs):
            if sc.shots:
                continue
            share = max(cfg.min_shots_per_scene,
                        -(-need * total_need // max(dialogue_need, 1)))
            sc._shot_budget = min(share, cfg.max_shots_per_scene)

        # how many shots the episode has already: the scenes that are done
        # count, and the ones about to be made are counted as they are
        # planned, so the budget is the same as it was when the scenes
        # were taken one after another
        made = sum(len(s.shots) for s in ep.scenes)
        for sc in ep.scenes:
            if sc.shots:
                continue
            narration_sec = round(sum(estimate_reading_seconds(l.text) for l in sc.lines), 1)
            # the lines are numbered for the model; the numbers it answers with
            # have to be translated back to the spoken lines only, because the
            # narration is never spoken
            lines_text = "\n".join(
                f"- {i}. {l.speaker}({l.emotion}): {l.text}"
                for i, l in enumerate(sc.lines, 1)) or "（无台词，纯画面）"
            # what this scene has to be seen doing: the beats the script
            # found in the novel, in order.  The question already asked
            # for "all the lines and all the action"; until now there was
            # no action to cover.
            beats_text = "\n".join(
                f"- {i}. {b.action}"
                + (f"（台词 {','.join(str(n) for n in b.lines)}）" if b.lines else "（无台词）")
                for i, b in enumerate(getattr(sc, "beats", []) or [], 1)
            ) or "（这一场没有拍点：只有台词）"
            spoken_at = [i for i, l in enumerate(sc.lines, 1)
                         if not is_narration(l)]
            spoken_pos = {full: k + 1 for k, full in enumerate(spoken_at)}
            # a short drama only holds attention if it cuts fast: the episode
            # gets a shot budget and every scene a share of what is left
            left = max(cfg.min_shots_per_scene,
                       cfg.max_shots_per_episode - made)
            want = getattr(sc, "_shot_budget", 0)
            max_shots = max(cfg.min_shots_per_scene,
                            min(cfg.max_shots_per_scene, left, want) if want
                            else min(cfg.max_shots_per_scene, left))
            made += max_shots
            # how long this scene is, and how long a segment of it is on
            # average: concrete numbers, so the plan lands where it should
            share = max(1, int(getattr(sc, "_shot_budget", 0) or 1))
            scene_seconds = int(round(episode_seconds * share
                                      / max(1, total_need)))
            scene_avg = round(scene_seconds / share, 1)
            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            director_rules=_rules,
                            # the look the whole drama is made in: the
                            # camera language of the plan belongs to it
                            style=(ctx.project.art_direction.style_prompt_prefix
                                   or ctx.project.art_direction.style or ""),
                            episode_seconds=episode_seconds,
                            avg_seconds=round(avg, 1),
                            scene_seconds=scene_seconds,
                            scene_avg=scene_avg,
                            scene_shots=share,
                            time_of_day=sc.time_of_day, mood=sc.mood, summary=sc.summary,
                            lines_text=lines_text, beats_text=beats_text,
                            segment_cuts=bool(ctx.cfg.comfyui.segment_cuts),
                            min_shots=cfg.min_shots_per_scene,
                            max_shots=max_shots, prefer_dynamic=prefer,
                            dur_min=dmin, dur_max=dmax, narration_seconds=narration_sec,
                            character_names=char_names,
                            **frame,
                            **_ref_rhythm_args(cfg.ref_rhythm))
            jobs.append((ep, sc, spoken_at, spoken_pos, user))
        eps_done.append(ep)

    # Every scene is its own question to the model, and the scenes of
    # different episodes do not wait on each other - so they are asked
    # together.
    def _one(job):
        ep, sc, spoken_at, spoken_pos, user = job
        data = pool.next().complete_json(system, user)
        if isinstance(data, list):
            data = data[0] if data else {}
        shots = []
        for i, s in enumerate(data.get("shots", []) or [], 0):
            # which lines this shot carries, so the cut can land on them
            idx: list[int] = []
            for v in (s.get("lines") or []):
                try:
                    n = int(v)
                except (TypeError, ValueError):
                    continue
                k = spoken_pos.get(n)
                if k and k not in idx:
                    idx.append(k)
            # which beats this shot films, so a beat that no shot
            # covers can be counted.  A beat number the scene does not
            # have is not a beat: the model counts them its own way.
            n_beats = len(getattr(sc, "beats", []) or [])
            covered: list[int] = []
            for v in (s.get("beats") or []):
                try:
                    n = int(v)
                except (TypeError, ValueError):
                    continue
                if 0 < n <= n_beats and n not in covered:
                    covered.append(n)
            shots.append(Shot(
                id=_id("sh"), index=i, shot_type=_to_shot_type(s.get("shot_type", "中景")),
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
        sc.shots = shots or _fallback_shots(sc, dmin, dmax)
        _repair_line_casts(sc)
        _repair_characters(ctx, sc)
        # a shot that carries too much dialogue gets a second shot
        _split_long_shots(sc)
        # the coverage rules: nobody talks to the lens, and no two
        # shots in a row are the same picture
        _enforce_coverage(sc)
        # the scene is saved as it arrives: a run that is stopped
        # halfway keeps the scenes that were already designed
        ctx.save()
        return len(shots)

    results = run_jobs(ctx, jobs, _one, workers=write_workers(ctx),
                       label="storyboard")

    # the answers go back in
    failed: set = set()
    for (job, _n, err) in results:
        ep, sc, _spoken_at, _spoken_pos, _user = job
        if err:
            ctx.log.error("storyboard: 第%d集 场%d 失败 %s", ep.index, sc.index, err)
            sc.status = Status.FAILED
            failed.add(ep.index)
            if ctx.cfg.pipeline.fail_fast:
                raise RuntimeError(err)
            # fallback: one shot per line so the pipeline still proceeds
            sc.shots = _fallback_shots(sc, dmin, dmax)
            ctx.save()

    for ep in eps_done:
        # The lengths are the director's.  They are only kept inside the
        # range the video model can render - a segment outside it cannot be
        # made at all.
        for sc in ep.scenes:
            for sh in sc.shots:
                sh.duration = round(max(dmin, min(dmax, float(sh.duration or dmin))), 2)
        ctx.mark(ep, "storyboard",
                 Status.FAILED if ep.index in failed else Status.DONE)
        ctx.save()
        done += 1
        # What is worth saying in this shape: the beats of the novel that
        # no shot filmed.  (How many segments are one take is the whole
        # film now, so it says nothing.)
        filmed = 0
        beats = 0
        for sc in ep.scenes:
            f, b = _beat_coverage(sc)
            filmed += f
            beats += b
        ctx.log.info("storyboard: 第%d集 → %d 镜", ep.index, ep.total_shots)
        if beats:
            ctx.log.info("storyboard: 第%d集 拍点 %d 个，拍到 %d 个（%d%%）",
                         ep.index, beats, filmed, int(filmed * 100 / beats))
            if filmed < beats:
                ctx.log.warning("storyboard: 第%d集有 %d 个拍点没被拍到",
                                ep.index, beats - filmed)
    return {"episodes_storyboarded": done}


# The size ladder: one step along it is the move a viewer reads as a cut.
_SIZE_LADDER = {
    "远景": "全景", "全景": "中景", "中景": "近景", "近景": "特写",
    "特写": "近景", "过肩": "近景", "主观": "近景", "空镜": "中景",
}
# The other side of the axis, for when the size cannot move.
_OTHER_ANGLE = {
    "斜侧": "正侧", "正侧": "斜侧", "后斜侧": "斜侧",
    "正面": "斜侧", "背面": "正侧",
}


def _shot_speakers(shot, spoken) -> list[str]:
    """Who talks in this shot."""
    out: list[str] = []
    for n in shot.line_indices or []:
        if 1 <= n <= len(spoken):
            name = spoken[n - 1].speaker
            if name and name not in out:
                out.append(name)
    return out


def camera_on(shot, spoken) -> str:
    """Who the camera is on.

    The speaker of the shot when they are in the frame, otherwise whoever
    is left in it - the person listening.  This is the person whose face
    the audience is looking at, and two shots of the same face are two
    shots of the same thing.
    """
    for name in _shot_speakers(shot, spoken):
        if name in (shot.characters or []):
            return name
    if shot.characters:
        return shot.characters[0]
    return ""


def _enforce_coverage(sc) -> int:
    """Turn a list of shots into a coverage plan.

    A model asked for "shots" gives one head-on close-up per line of
    dialogue: every face square to the lens, every cut the same cut, and
    the whole thing reads as one camera on one tripod.  The rules here are
    mechanical, so they are enforced here rather than asked for in the
    prompt - a prompt is a request, this is the answer.

    What is fixed:

      - a shot that carries dialogue is never square to the lens
      - two shots in a row differ in size, in angle or in subject
      - nobody is left with three shots of their own face in a row: the
        middle one becomes the other person's shoulder in the foreground

    The speaker stays in frame.  The voice comes out of the clip, so the
    person who talks has to be the one on screen - what changes is the
    camera, not the cast.
    """
    shots = sc.shots
    if not shots:
        return 0
    spoken = [l for l in sc.lines if not is_narration(l)]
    changed = 0

    def speakers_of(shot) -> list[str]:
        return _shot_speakers(shot, spoken)

    def camera_on(shot) -> str:  # noqa: F811 - the local one knows the scene
        for name in speakers_of(shot):
            if name in (shot.characters or []):
                return name
        if shot.characters:
            return shot.characters[0]
        return ""

    # 1. a talking head is never square to the lens
    for shot in shots:
        # what the model wrote about the subject is better than anything
        # worked out here - "合同与父亲医药费缴费单" says more than a name
        if not shot.subject:
            shot.subject = camera_on(shot) or "环境"
        if shot.angle == "正面" and speakers_of(shot):
            # a wide shot may stand square to the room; a face in close-up
            # doing so is an interview, not a scene
            if shot.shot_type not in (ShotType.WIDE, ShotType.FULL):
                shot.angle = "斜侧"
                changed += 1

    # 2. nobody gets three shots of their own face in a row: the middle
    #    one becomes the other person's shoulder in the foreground
    def frame(shot) -> tuple:
        return (shot.shot_type.value, shot.angle)

    i = 0
    while i + 2 < len(shots):
        a, b, c = shots[i], shots[i + 1], shots[i + 2]
        on_a, on_b, on_c = camera_on(a), camera_on(b), camera_on(c)
        if on_a and on_a == on_b == on_c:
            # unless the middle one already looks like another picture
            if frame(b) == frame(a) or frame(b) == frame(c):
                other = _other_character(sc, b)
                b.shot_type = ShotType.OVER_SHOULDER
                b.angle = "后斜侧"
                if other and other not in (b.characters or []):
                    # the other person is in the foreground now - their
                    # shoulder and the back of their head
                    b.characters = list(b.characters or []) + [other]
                    if other not in (b.action or ""):
                        b.action = (f"{other}的肩与后脑在前景，"
                                    f"{b.action or ''}").strip("，")
                changed += 1
            i += 1
        else:
            i += 1

    # 3. two shots in a row have to be different pictures
    for i in range(1, len(shots)):
        a, b = shots[i - 1], shots[i]
        if (a.shot_type == b.shot_type and a.angle == b.angle
                and camera_on(a) and camera_on(a) == camera_on(b)):
            # the size moves first: a change of size is what reads as a cut
            step = _SIZE_LADDER.get(b.shot_type.value, "")
            if step and step != b.shot_type.value:
                b.shot_type = _to_shot_type(step)
            else:
                b.angle = _OTHER_ANGLE.get(b.angle, "正侧")
            changed += 1
    return changed


def _other_character(sc, shot) -> str:
    """Someone in the scene who is not the one the shot is about."""
    names: list[str] = []
    for line in sc.lines:
        name = (line.speaker or "").strip()
        if name and name not in ("旁白", "解说", "旁白者") and name not in names:
            names.append(name)
    subject = shot.subject or ""
    for name in names:
        if name != subject:
            return name
    return ""


def _repair_characters(ctx, sc) -> int:
    """Make the shot's list agree with its action, speaker first.

    The picture is drawn from the action and the video is given reference
    sheets of the people in the list, so the two have to agree.  The person
    who speaks the shot goes first: <Subject 1> is the person in
    <Picture 1>, <Subject 1> is the one who speaks, and <Audio 1> is the
    timbre reference for that same person.
    """
    names = [c.name for c in ctx.project.characters if c.name]
    spoken = [l for l in sc.lines if not is_narration(l)]
    changed = 0
    for shot in sc.shots:
        action = shot.action or ""
        # the people the action puts in the frame, in the order it puts
        # them there
        named = []
        for n in names:
            at = action.find(n)
            if at >= 0:
                named.append((at, n))
        named = [n for _at, n in sorted(named)]
        if not named:
            continue
        # the one who speaks the shot comes first
        first = ""
        for idx in (shot.line_indices or []):
            if 1 <= idx <= len(spoken):
                spk = spoken[idx - 1].speaker
                if spk in named:
                    first = spk
                    break
        keep = [n for n in (shot.characters or []) if n in named]
        merged = list(dict.fromkeys(([first] if first else []) + named + keep))
        if merged != (shot.characters or []):
            shot.characters = merged
            changed += 1
    return changed


def _repair_line_casts(sc) -> int:
    """Move a line to a shot that actually has the speaker in frame.

    The model sometimes puts a line on the other character's shot. A
    reaction shot is fine now and then, but when an empty shot with the
    speaker in it is available, the line belongs there - otherwise the
    viewer hears one person and sees another.

    The voice comes out of the clip itself, so a line whose speaker is
    not in the picture has no sound at all.  So the line is moved to a
    shot that has the speaker in it: first one that is free, then one
    with room.  Only when no shot in the scene has the speaker does the
    speaker get put into this shot - which is the one case where the
    line cannot be moved.
    """
    spoken = [l for l in sc.lines if not is_narration(l)]
    if not spoken:
        return 0
    moved = 0
    for shot in sc.shots:
        if not shot.line_indices:
            continue
        for n in list(shot.line_indices):
            if not (1 <= n <= len(spoken)):
                continue
            line = spoken[n - 1]
            if line.speaker in (shot.characters or []):
                continue
            # an empty shot with the speaker in it?
            for other in sc.shots:
                if other is shot or other.line_indices:
                    continue
                if line.speaker in (other.characters or []):
                    shot.line_indices.remove(n)
                    other.line_indices.append(n)
                    moved += 1
                    break
            else:
                # no free shot: a shot that has the speaker and has room
                for other in sc.shots:
                    if other is shot:
                        continue
                    if line.speaker not in (other.characters or []):
                        continue
                    if len(other.line_indices or []) >= 2:
                        continue
                    shot.line_indices.remove(n)
                    other.line_indices.append(n)
                    moved += 1
                    break
    # the people who speak in a shot are in that shot - unless the shot
    # already has somebody in it, and then this is the reaction shot:
    # the listener is on screen and the speaker is not
    for shot in sc.shots:
        names = list(shot.characters or [])
        if not names:
            for n in shot.line_indices:
                if 1 <= n <= len(spoken):
                    spk = spoken[n - 1].speaker
                    if spk and spk not in names:
                        names.append(spk)
        shot.characters = names
    for shot in sc.shots:
        shot.line_indices.sort()
    return moved


# a shot carries at most this much dialogue: a short drama cuts fast
SHOT_DIALOGUE_MAX = 3.5

# the second half of a split shot must not look like the first half
_SPLIT_FRAMING = {
    "特写": "近景", "近景": "特写", "中景": "近景", "过肩": "特写",
    "全景": "中景", "远景": "全景", "主观": "特写", "空镜": "中景",
}


def _split_action(action: str, texts: list[str]) -> tuple[str, str]:
    """Cut the action description at the first of the lines that moves.

    The model often runs two lines together inside one pair of quotes, so
    the exact quote is not always there: the line's own text is used to
    find the place, and a quote left dangling at the end of the first half
    is moved over to the second.
    """
    text = action or ""
    pos = -1
    for t in texts:
        found = -1
        for q in (f"“{t}”", f"「{t}」", f'"{t}"'):
            i = text.find(q)
            if i >= 0:
                found = i
                break
        if found < 0:
            found = text.find(t)
        if found >= 0:
            pos = found if pos < 0 else min(pos, found)
    if pos < 0:
        return text, ""
    head = text[:pos].rstrip("，,、 ")
    tail = text[pos:].lstrip()
    if head.endswith(("“", "「", '"')):
        head = head[:-1].rstrip()
        tail = "“" + tail
    return head, tail


def _split_long_shots(sc, max_dialogue: float = SHOT_DIALOGUE_MAX) -> int:
    """Give a shot that carries too much dialogue a second shot.

    Three sentences in one shot is six seconds of one face, and a short
    drama cuts away. The lines that do not fit move into a new shot right
    behind it, with a different framing so the cut reads as a cut and not
    as a jump.
    """
    spoken = [l for l in sc.lines if not is_narration(l)]
    if not spoken:
        return 0
    added = 0
    i = 0
    while i < len(sc.shots):
        shot = sc.shots[i]
        idxs = [n for n in shot.line_indices if 1 <= n <= len(spoken)]
        if len(idxs) < 2:
            i += 1
            continue
        durs = [estimate_reading_seconds(spoken[n - 1].text) for n in idxs]
        keep = 0
        total = 0.0
        for k, d in enumerate(durs):
            if keep and (total + d > max_dialogue or keep >= 2):
                break
            if not keep and d > max_dialogue:
                break
            total += d
            keep = k + 1
        if keep >= len(idxs):
            i += 1
            continue
        moved = idxs[keep:]
        head, tail = _split_action(shot.action or "",
                                   [spoken[n - 1].text for n in moved])
        shot.line_indices = idxs[:keep]
        if head:
            shot.action = head
        rest = Shot(
            id=_id("sh"),
            index=shot.index + 1,
            shot_type=_to_shot_type(
                _SPLIT_FRAMING.get(shot.shot_type.value, "近景")),
            camera_move=shot.camera_move,
            # the second half of a shot has to look like another picture,
            # not like the first half again
            angle=_OTHER_ANGLE.get(shot.angle, "正侧"),
            height=shot.height,
            lens=shot.lens,
            purpose=shot.purpose,
            subject=shot.subject,
            duration=shot.duration,
            action=(f"接上：{tail}" if tail else f"接上：{shot.action or ''}"),
            characters=list(shot.characters),
            line_indices=sorted(moved),
        )
        sc.shots.insert(i + 1, rest)
        added += 1
        i += 1
    for n, shot in enumerate(sc.shots):
        shot.index = n
    return added


def _fit_durations(shots: list[Shot], target: float,
                   dmin: float, dmax: float) -> float:
    """Make the segments of an episode fill the episode.

    Every segment comes back with the length the model gave it, and the sum
    of them is whatever it happened to be.  The episode has a length to hit -
    five minutes - so the segments are scaled to it, each one staying inside
    the range a segment is allowed to have.
    """
    if not shots:
        return 0.0
    total = sum(float(s.duration or 0.0) for s in shots)
    if total <= 0:
        return 0.0
    k = float(target) / total
    for s in shots:
        s.duration = max(dmin, min(dmax, float(s.duration or dmin) * k))
    # The segments that hit the ends of the range took the difference out of
    # the others; the difference is given back to the ones that have room.
    for _ in range(6):
        cur = sum(float(s.duration) for s in shots)
        diff = float(target) - cur
        if abs(diff) < 0.05:
            break
        free = [s for s in shots
                if dmin + 0.01 < float(s.duration) < dmax - 0.01]
        if not free:
            break
        share = diff / len(free)
        for s in free:
            s.duration = max(dmin, min(dmax, float(s.duration) + share))
    for s in shots:
        s.duration = round(float(s.duration), 2)
    return round(sum(float(s.duration) for s in shots), 2)


def _fallback_shots(sc, dmin: float, dmax: float) -> list[Shot]:
    """One medium shot per line (or a single shot for a silent scene).

    The fallback still has to obey the coverage rules, so the angle
    alternates and nobody is left with the same picture twice.
    """
    shots: list[Shot] = []
    items = sc.lines or [None]  # type: ignore[list-item]
    spoken_no = 0
    for i, l in enumerate(items):
        action = l.text[:60] if l else sc.summary[:60]
        idxs: list[int] = []
        if l and not is_narration(l):
            spoken_no += 1
            idxs = [spoken_no]
        chars = [l.speaker] if (l and l.speaker not in ("旁白", "解说")) else []
        # each shot carries the line it was made for, so the cut lands on it
        shots.append(Shot(id=_id("sh"), index=i, shot_type=ShotType.MEDIUM,
                          camera_move="固定", duration=max(dmin, min(dmax, 3.0)),
                          angle=("斜侧" if i % 2 == 0 else "正侧"),
                          height="平视", lens="标准",
                          subject=(chars[0] if chars else "环境"),
                          action=action, characters=chars, line_indices=idxs))
    return shots
