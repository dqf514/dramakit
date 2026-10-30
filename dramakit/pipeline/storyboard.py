"""Stage 5 — storyboard: design the shot list for every scene."""
from __future__ import annotations

import uuid

from ..models import Shot, ShotType, Status, is_narration
from ..prompts import templates as T
from ..utils.text import estimate_reading_seconds
from .base import Context


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _to_shot_type(v: str) -> ShotType:
    v = (v or "").strip()
    for st in ShotType:
        if st.value == v or st.name.lower() == v.lower():
            return st
    return ShotType.MEDIUM


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


def run(ctx: Context) -> dict:
    cfg = ctx.cfg.storyboard
    llm = ctx.providers.llm_for("storyboard")
    char_names = ", ".join(c.name for c in ctx.project.characters) or "（自行判断）"
    dmin, dmax = (cfg.shot_duration_range + [2.0, 5.0])[:2]
    done = 0
    for ep in ctx.target_episodes():
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
            needs.append(want)
        total_need = sum(needs)
        budget = max(cfg.max_shots_per_episode, total_need)
        for sc, need in zip(ep.scenes, needs):
            if sc.shots:
                continue
            share = max(cfg.min_shots_per_scene,
                        -(-need * budget // max(total_need, 1)))
            sc._shot_budget = share        # type: ignore[attr-defined]

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
            spoken_at = [i for i, l in enumerate(sc.lines, 1)
                         if not is_narration(l)]
            spoken_pos = {full: k + 1 for k, full in enumerate(spoken_at)}
            prefer = "多用运动镜头增强节奏" if cfg.prefer_dynamic else "以固定镜头为主"
            # a short drama only holds attention if it cuts fast: the episode
            # gets a shot budget and every scene a share of what is left
            left = max(cfg.min_shots_per_scene,
                       cfg.max_shots_per_episode - sum(len(s.shots) for s in ep.scenes))
            want = getattr(sc, "_shot_budget", 0)
            max_shots = max(cfg.min_shots_per_scene,
                            min(cfg.max_shots_per_scene, left, want) if want
                            else min(cfg.max_shots_per_scene, left))
            from ..skills.film import DIRECTOR_RULES
            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            director_rules=DIRECTOR_RULES,
                            time_of_day=sc.time_of_day, mood=sc.mood, summary=sc.summary,
                            lines_text=lines_text, min_shots=cfg.min_shots_per_scene,
                            max_shots=max_shots, prefer_dynamic=prefer,
                            dur_min=dmin, dur_max=dmax, narration_seconds=narration_sec,
                            character_names=char_names,
                            **_ref_rhythm_args(cfg.ref_rhythm))
            try:
                data = llm.complete_json(T.STORYBOARD_SYSTEM, user)
            except Exception as e:  # noqa: BLE001
                ctx.log.error("storyboard: 第%d集 场%d 失败 %s", ep.index, sc.index, e)
                sc.status = Status.FAILED
                if ctx.cfg.pipeline.fail_fast:
                    raise
                # fallback: one shot per line so the pipeline still proceeds
                sc.shots = _fallback_shots(sc, dmin, dmax)
                continue
            if isinstance(data, list):
                data = data[0] if data else {}
            shots = []
            n_lines = len(spoken_at)
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
                shots.append(Shot(
                    id=_id("sh"), index=i, shot_type=_to_shot_type(s.get("shot_type", "中景")),
                    camera_move=s.get("camera_move", "固定"),
                    duration=_clamp(s.get("duration"), dmin, dmax, 3.0),
                    action=s.get("action", ""),
                    characters=[str(c) for c in (s.get("characters") or [])],
                    line_indices=sorted(idx),
                ))
            sc.shots = shots or _fallback_shots(sc, dmin, dmax)
            _repair_line_casts(sc)
            # a shot that carries too much dialogue gets a second shot
            _split_long_shots(sc)
        ctx.mark(ep, "storyboard", Status.DONE)
        ctx.save()
        done += 1
        ctx.log.info("storyboard: 第%d集 → %d 镜", ep.index, ep.total_shots)
    return {"episodes_storyboarded": done}


def _repair_line_casts(sc) -> int:
    """Move a line to a shot that actually has the speaker in frame.

    The model sometimes puts a line on the other character's shot. A
    reaction shot is fine now and then, but when an empty shot with the
    speaker in it is available, the line belongs there - otherwise the
    viewer hears one person and sees another.

    Whatever happens, the people who speak in a shot are put into that
    shot: the shot's picture is made from its characters, so a speaker who
    is not in the list is a voice with nobody behind it.
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
    # everybody who speaks in a shot is in that shot
    for shot in sc.shots:
        names = list(shot.characters or [])
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


def _fallback_shots(sc, dmin: float, dmax: float) -> list[Shot]:
    """One medium shot per line (or a single shot for a silent scene)."""
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
                          action=action, characters=chars, line_indices=idxs))
    return shots
