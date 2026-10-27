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
        # every scene gets the shots its own lines need - two lines per shot
        # is the rhythm a short drama runs at
        needs = []
        for sc in ep.scenes:
            spoken = sum(1 for l in sc.lines if not is_narration(l))
            needs.append(max(cfg.min_shots_per_scene, -(-spoken // 2)))
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
            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            time_of_day=sc.time_of_day, mood=sc.mood, summary=sc.summary,
                            lines_text=lines_text, min_shots=cfg.min_shots_per_scene,
                            max_shots=max_shots, prefer_dynamic=prefer,
                            dur_min=dmin, dur_max=dmax, narration_seconds=narration_sec,
                            character_names=char_names)
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
    for shot in sc.shots:
        shot.line_indices.sort()
    return moved


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
