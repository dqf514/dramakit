"""Compare the timeline of an episode with the subtitles that were written."""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.pipeline.base import build_timeline
from dramakit.project import ProjectStore

proj = Path(r"E:\dramakit\projects") / sys.argv[1]
store = ProjectStore(proj)
p = store.load()
ep = p.episodes[0]
tl = build_timeline(ep)

ass = next(proj.rglob("ep_001.ass"))
cues = []
for line in ass.read_text(encoding="utf-8").splitlines():
    if not line.startswith("Dialogue:"):
        continue
    f = line.split(",", 9)
    if f[3] not in ("Default", "Narration"):
        continue
    h, m, rest = f[1].split(":")
    t0 = int(h) * 3600 + int(m) * 60 + float(rest)
    h, m, rest = f[2].split(":")
    t1 = int(h) * 3600 + int(m) * 60 + float(rest)
    cues.append((t0, t1, f[3], re.sub(r"\{[^}]*\}", "", f[-1]).strip()))

print(f"{'时间线':>26}  {'字幕':>26}")
for t in tl.lines:
    l = t.line
    if not l.text.strip():
        continue
    match = [c for c in cues if abs(c[0] - t.start) <= 0.3]
    tag = f"{t.start:6.2f}-{t.end:6.2f} {l.kind.value[:4]} {l.speaker[:6]}"
    if match:
        c = match[0]
        print(f"{tag:30s} | {c[0]:6.2f}-{c[1]:6.2f} {c[3][:22]}")
    else:
        near = [c for c in cues if c[0] < t.end and c[1] > t.start]
        extra = f"   附近字幕: {near[0][0]:.2f}-{near[0][1]:.2f} {near[0][3][:16]}" \
            if near else "   （附近也没有）"
        print(f"{tag:30s} | ** 缺字幕 **{extra}   台词: {l.text[:20]}")
