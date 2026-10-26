"""Step through the subtitle stage for one episode, printing everything."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.media.subtitle import write_ass
from dramakit.models import SubtitleCue, is_narration
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
proj = Path(r"E:\dramakit\projects") / sys.argv[1]
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
tl = build_timeline(ep)

MIN_CUE = 0.8
cues: list[SubtitleCue] = []
for tsc in tl.scenes:
    for tl_line in tsc.lines:
        l = tl_line.line
        if not l.text.strip():
            continue
        start = tl_line.start
        end = max(tl_line.end, start + MIN_CUE)
        narr = is_narration(l)
        cues.append(SubtitleCue(start=round(start, 3), end=round(end, 3),
                                 speaker="" if narr else l.speaker,
                                 text=l.text, kind=l.kind))
        print(f"  构造: {start:7.3f} -> {end:7.3f}  dur={end-start:6.3f} "
              f"line.dur={l.duration:6.3f}  「{l.text[:16]}」")

cues.sort(key=lambda c: c.start)
print("排序+去重叠之后:")
for i in range(len(cues) - 1):
    cur, nxt = cues[i], cues[i + 1]
    if cur.kind != nxt.kind:
        continue
    if cur.end > nxt.start:
        print(f"  裁剪: {cur.text[:14]} {cur.start:.2f}-{cur.end:.2f} -> "
              f"nxt.start={nxt.start:.2f}  max(MIN_CUE,{nxt.start - 0.02:.2f})="
              f"{max(MIN_CUE, nxt.start - 0.02):.2f}")
        cur.end = max(MIN_CUE, nxt.start - 0.02)
for c in cues[:6]:
    print(f"  {c.start:7.3f} -> {c.end:7.3f}  「{c.text[:18]}」")
