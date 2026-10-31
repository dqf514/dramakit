"""The windows of the shots have to tile exactly.

The shot's start was rounded and its duration was rounded, but the cursor
that walked along the scene added up the unrounded durations - so the
start of one shot and the end of the one before it were a fraction of a
millisecond apart.  A line that belongs to a shot starts exactly when that
shot starts, and it landed in the tail of the shot before it: every line
was one shot early, the prompts and the picture disagreed about who says
what, and the subtitle was a line off.

So the cursor walks over the rounded durations: the end of one shot is the
start of the next, to the last decimal.
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


patch("dramakit/pipeline/base.py", [
    ("""            shot_cursor = cursor
            for i, sh in enumerate(sc.shots):
                d = shot_durs[i] * scale
                if i == len(sc.shots) - 1:               # absorb rounding on last
                    d = scene_dur - (shot_cursor - cursor)
                d = max(d, min_shot)
                timed_shots.append(TimedShot(sh, round(shot_cursor, 3), round(d, 3)))
                shot_cursor += d""",
     """            shot_cursor = cursor
            for i, sh in enumerate(sc.shots):
                d = shot_durs[i] * scale
                if i == len(sc.shots) - 1:               # absorb rounding on last
                    d = scene_dur - (shot_cursor - cursor)
                d = round(max(d, min_shot), 3)
                # the cursor walks over the rounded duration, so the end of
                # one shot is the start of the next: a line that belongs to
                # a shot starts exactly when that shot starts, and it must
                # not fall into the tail of the shot before it
                timed_shots.append(TimedShot(sh, round(shot_cursor, 3), d))
                shot_cursor += d"""),
])

patch("dramakit/pipeline/promptgen.py", [
    ("""            for ts in tsc.shots:
                if ts.start <= tl_line.start < ts.start + ts.duration:
                    out.setdefault(ts.shot.id, []).append(
                        (tl_line.line.speaker, tl_line.line.text,
                         float(tl_line.line.duration or 0.0)))
                    break""",
     """            # The line belongs to the shot that is on screen when it is
            # said: the last one that has started.
            owner = None
            for ts in tsc.shots:
                if ts.start - 0.02 <= tl_line.start < ts.start + ts.duration:
                    owner = ts
            if owner is not None:
                out.setdefault(owner.shot.id, []).append(
                    (tl_line.line.speaker, tl_line.line.text,
                     float(tl_line.line.duration or 0.0)))"""),
])
