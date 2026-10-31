"""The measurements have to know what a segment is.

A line of the storyboard is a segment of six to fifteen seconds, and the
model cuts inside it.  The QA still measured in "shots", so it called a
nine second segment "slow" and a hook that arrives in the first second
"late".

The thresholds now come from the range the format asks for, and the pitch
of a voice is read between the samples: the autocorrelation only gives
whole-sample lags, and two voices two samples apart used to come out as
the same number.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\qa.py")
s = p.read_text(encoding="utf-8")

# --------------------------------------------------------------------------- #
# 1. the segment range
# --------------------------------------------------------------------------- #
old = """        limit = 12.0 if len(lines) <= 1 else 16.0
        if ts.duration > limit:"""
new = """        # a segment is six to fifteen seconds; it may run over when the
        # line it carries needs the room
        limit = _segment_max(ctx) + 3.0
        if ts.duration > limit:"""
assert old in s, "pacing 的镜头长度锚点没找到"
s = s.replace(old, new, 1)

old = """    durs = [ts.duration for ts in tl.shots]
    avg = sum(durs) / len(durs) if durs else 0.0
    if durs and avg > 5.0:
        issues.append(("pacing", "slow_average", "-",
                       f"平均镜头 {avg:.1f}s，偏慢（短剧通常 2~3 秒一刀）"))"""
new = """    durs = [ts.duration for ts in tl.shots]
    avg = sum(durs) / len(durs) if durs else 0.0
    if durs and avg > _segment_max(ctx):
        issues.append(("pacing", "slow_average", "-",
                       f"平均片段 {avg:.1f}s，偏慢（一个片段 "
                       f"{_segment_min(ctx):.0f}~{_segment_max(ctx):.0f} 秒，"
                       f"段内还有切点）"))"""
assert old in s, "pacing 的平均锚点没找到"
s = s.replace(old, new, 1)

# the helper
old = """def check_pacing(ctx, ep, tl, issues):"""
new = '''def _segment_range(ctx) -> tuple[float, float]:
    """The length a segment is allowed to have."""
    try:
        rng = list(ctx.cfg.storyboard.shot_duration_range or [])
        lo = float(rng[0]) if rng else 6.0
        hi = float(rng[1]) if len(rng) > 1 else 15.0
        return lo, hi
    except Exception:  # noqa: BLE001
        return 6.0, 15.0


def _segment_min(ctx) -> float:
    return _segment_range(ctx)[0]


def _segment_max(ctx) -> float:
    return _segment_range(ctx)[1]


def check_pacing(ctx, ep, tl, issues):'''
assert old in s, "check_pacing 锚点没找到"
s = s.replace(old, new, 1)

# --------------------------------------------------------------------------- #
# 2. the pitch between the samples
# --------------------------------------------------------------------------- #
old = """        found = 0
        for i, v in enumerate(row):
            if v >= best * 0.9:
                found = i
                break
        if found:
            found_pitches.append(rate2 / (lo + found))"""
new = """        found = 0
        for i, v in enumerate(row):
            if v >= best * 0.9:
                found = i
                break
        if found:
            # the peak sits between two lags: the autocorrelation only
            # knows whole samples, and two voices a sample apart used to
            # come out as the same number
            lag = float(found)
            if 0 < found < len(row) - 1:
                y0, y1, y2 = row[found - 1], row[found], row[found + 1]
                den = (y0 - 2 * y1 + y2)
                if den:
                    lag += 0.5 * (y0 - y2) / den
            found_pitches.append(rate2 / (lo + lag))"""
assert old in s, "基频锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("qa.py: 片段长度口径和基频分辨率都改好了")
