"""The episode has to be five minutes of six-to-fifteen-second segments.

What was wrong:

  * The timeline let the dialogue decide how long a shot was.  A shot that
    carried one short line became three seconds long, while the H3 prompt
    told the model to play seven seconds of business inside it.  The clip and
    its own instruction disagreed, and the episode came out at 102 seconds
    instead of five minutes.

  * The storyboard took the number of segments from the length of the
    dialogue and never from the length of the episode, so the segments did
    not add up to the time the episode was supposed to last.

The fix:

  * The director's segment is the shot's length.  The dialogue fits inside
    it; it never shortens it.
  * The segments of an episode are scaled to the episode's target length,
    each one staying inside the range a segment is allowed to have.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")


def patch(path: str, pairs: list[tuple[str, str]]) -> None:
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s and old not in s:
            print(f"  {path}: 已经打过补丁了")
            continue
        assert old in s, f"{path}: 锚点没找到\n{old[:200]}"
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"  {path}: 改好了")


# --------------------------------------------------------------------------- #
# 1. the timeline: the segment decides the length, the dialogue fits in
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/base.py", [
    ("""        shot_durs: list[float] = []
        for i, sh in enumerate(sc.shots):
            d = max(sh.duration, min_shot)
            if line_map:
                idxs = line_map.get(sh.id) or []
                owned = sum(raw_lines[i - 1][0] for i in idxs)
                if owned > 0:
                    d = owned + gap * max(0, len(idxs) - 1)
                    if i != last_line_shot:
                        d += gap
            shot_durs.append(d)""",
     """        shot_durs: list[float] = []
        for i, sh in enumerate(sc.shots):
            # The director's segment is the shot's length.  A segment is six
            # to fifteen seconds and holds several shots inside it; the
            # dialogue has to fit inside the segment, it never shortens it.
            # (A shot shortened to the length of its words ends up with a
            # prompt that asks for seven seconds of business inside three
            # seconds of clip.)
            d = max(sh.duration, min_shot)
            if max_shot > 0:
                d = min(d, max_shot)
            if line_map:
                idxs = line_map.get(sh.id) or []
                owned = sum(raw_lines[i - 1][0] for i in idxs)
                if owned > 0:
                    need = owned + gap * max(0, len(idxs) - 1)
                    d = max(d, need)
            shot_durs.append(d)"""),
    # the timeline is built with the range a segment is allowed to have
    ("""        return build_timeline(ep,
                              max_shot=self.cfg.comfyui.max_video_seconds,
                              line_gap=self.cfg.compose.line_gap)""",
     """        rng = list(self.cfg.storyboard.shot_duration_range or [])
        dmin = float(rng[0]) if rng else 6.0
        dmax = float(rng[1]) if len(rng) > 1 else 15.0
        cap = float(self.cfg.comfyui.max_video_seconds or 0) or dmax
        return build_timeline(ep,
                              min_shot=dmin,
                              max_shot=min(dmax, cap),
                              line_gap=self.cfg.compose.line_gap)"""),
])


# --------------------------------------------------------------------------- #
# 2. the storyboard: the segments fill the episode
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/storyboard.py", [
    ("""        needs = []
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
            sc._shot_budget = share        # type: ignore[attr-defined]""",
     """        needs = []
        for sc in ep.scenes:
            spoken = [l for l in sc.lines if not is_narration(l)]
            secs = sum(estimate_reading_seconds(l.text) for l in spoken) * 1.2
            want = max(cfg.min_shots_per_scene, (int(secs * 100) + 349) // 350)
            needs.append(want)
        dialogue_need = sum(needs)
        # The episode has a length to hit - five minutes - and a segment is
        # six to fifteen seconds, so the episode needs about thirty of them.
        # The number of segments is decided by the length of the episode and
        # by the dialogue it has to hold, whichever asks for more.
        target = float(ep.duration_target or cfg.segment.episode_duration)
        avg = (dmin + dmax) / 2.0
        length_need = max(1, int(round(target / avg)))
        total_need = max(dialogue_need, length_need)
        for sc, need in zip(ep.scenes, needs):
            if sc.shots:
                continue
            share = max(cfg.min_shots_per_scene,
                        -(-need * total_need // max(dialogue_need, 1)))
            sc._shot_budget = min(share, cfg.max_shots_per_scene)"""),
    # the number of segments per scene is asked for by name
    ("""            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            director_rules=DIRECTOR_RULES,""",
     """            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            director_rules=DIRECTOR_RULES,
                            episode_seconds=int(target),
                            avg_seconds=round(avg, 1),"""),
    # after the scenes are done, the segments are scaled to the episode
    ("""            sc.shots = shots or _fallback_shots(sc, dmin, dmax)
            _repair_line_casts(sc)
            # a shot that carries too much dialogue gets a second shot
            _split_long_shots(sc)
        ctx.mark(ep, "storyboard", Status.DONE)""",
     """            sc.shots = shots or _fallback_shots(sc, dmin, dmax)
            _repair_line_casts(sc)
            # a shot that carries too much dialogue gets a second shot
            _split_long_shots(sc)
        # the segments of the episode are scaled so that they fill it
        _fit_durations([sh for sc in ep.scenes for sh in sc.shots],
                       target, dmin, dmax)
        ctx.mark(ep, "storyboard", Status.DONE)"""),
    # the helper
    ("""def _fallback_shots(sc, dmin: float, dmax: float) -> list[Shot]:""",
     '''def _fit_durations(shots: list[Shot], target: float,
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
        s.duration = round(max(dmin, min(dmax, float(s.duration or dmin) * k)), 2)
    return round(sum(float(s.duration) for s in shots), 2)


def _fallback_shots(sc, dmin: float, dmax: float) -> list[Shot]:'''),
])


# --------------------------------------------------------------------------- #
# 3. the prompt tells the model the length the episode has
# --------------------------------------------------------------------------- #
patch("dramakit/prompts/templates.py", [
    ("""- 生成 {{min_shots}}~{{max_shots}} 个镜头，覆盖本场全部台词与动作""",
     """- 生成 {{min_shots}}~{{max_shots}} 个镜头，覆盖本场全部台词与动作
- **这一集总共约 {{episode_seconds}} 秒**，一个片段 {{dur_min}}~{{dur_max}} 秒，
  平均每个片段约 {{avg_seconds}} 秒。请按这个密度给片段排长度，
  让本场加起来的时长贴近本集在全片中占的那一份"""),
    ("""- 镜头时长之和应≈本场台词总时长({{narration_seconds}}秒)""",
     """- 台词总时长约 {{narration_seconds}} 秒；片段比台词长出来的那部分是表演、
  反应和环境，**镜头时长之和不必等于台词总时长**"""),
])

print("补丁打完")
