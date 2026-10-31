"""The segments of an episode have to add up to the episode.

The segments are scaled to the length of the episode, but a segment is not
allowed to be shorter than six seconds or longer than fifteen, and the
ones that hit the ends take the difference out of the others: an episode
that should be five minutes came out at five minutes and forty-six
seconds.

So the difference is given back to the segments that have room for it.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\storyboard.py")
s = p.read_text(encoding="utf-8")

old = '''    total = sum(float(s.duration or 0.0) for s in shots)
    if total <= 0:
        return 0.0
    k = float(target) / total
    for s in shots:
        s.duration = round(max(dmin, min(dmax, float(s.duration or dmin) * k)), 2)
    return round(sum(float(s.duration) for s in shots), 2)'''

new = '''    total = sum(float(s.duration or 0.0) for s in shots)
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
    return round(sum(float(s.duration) for s in shots), 2)'''

assert old in s, "_fit_durations 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("storyboard.py: 片段时长会加总到一集的长度")
