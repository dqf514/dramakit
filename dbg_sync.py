"""Do the subtitles line up with the speech in the finished episode?

The speech onsets are measured from the final mix; the cue times come from
the subtitle file. If they drift, the viewer reads the wrong words.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

name = sys.argv[1]
proj = Path(r"E:\dramakit\projects") / name
ep = proj / "episodes" / "ep_001.mp4"

# speech onsets: the momentary loudness of the episode, then the moments
# where it jumps up (a line starting)
vals = ff.momentary_lufs(ep)
step = 0.1
onsets = []
prev = None
for i, v in enumerate(vals):
    if prev is not None and v > prev + 6 and v > -40:
        onsets.append(i * step)
    prev = v

ass = next(proj.rglob("ep_001.ass"))
cues = []
for line in ass.read_text(encoding="utf-8").splitlines():
    if not line.startswith("Dialogue:"):
        continue
    f = line.split(",", 9)
    if f[3] != "Default":
        continue
    h, m, rest = f[1].split(":")
    t0 = int(h) * 3600 + int(m) * 60 + float(rest)
    cues.append((t0, re.sub(r"\{[^}]*\}", "", f[-1]).strip()))

print(f"{name}: 成片 {ff.probe_duration(ep):.1f}s，检测到 {len(onsets)} 个语音起点，"
      f"{len(cues)} 条字幕")
print(f"{'字幕时间':>9}  {'文字':<20} 最近的语音起点  偏差")
for t0, text in cues:
    if not onsets:
        break
    near = min(onsets, key=lambda o: abs(o - t0))
    d = near - t0
    flag = "  <-- 偏差大" if abs(d) > 0.6 else ""
    print(f"{t0:9.2f}  {text[:20]:<20} {near:8.2f}       {d:+.2f}s{flag}")
