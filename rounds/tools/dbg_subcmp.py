"""Compare the subtitle cues with the timeline, line by line."""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
name = sys.argv[1]
store = ProjectStore(Path(r"E:\dramakit\projects") / name)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
tl = build_timeline(ep, max_shot=cfg.comfyui.max_video_seconds,
                    line_gap=cfg.compose.line_gap)

ass = Path(r"E:\dramakit\projects") / name / "subs" / "ep_001.ass"
cues = []
for line in ass.read_text(encoding="utf-8").splitlines():
    if not line.startswith("Dialogue:"):
        continue
    f = line.split(",", 9)
    h, m, rest = f[1].split(":")
    t0 = int(h) * 3600 + int(m) * 60 + float(rest)
    h, m, rest = f[2].split(":")
    t1 = int(h) * 3600 + int(m) * 60 + float(rest)
    cues.append((t0, t1, f[3], re.sub(r"\{[^}]*\}", "", f[-1]).strip()))

print(f"时间线总长 {tl.duration:.2f}s   字幕 {len(cues)} 条")
for t in tl.lines:
    if t.line.kind.value != "dialogue":
        continue
    hit = [c for c in cues if c[2] == "Default" and abs(c[0] - t.start) <= 0.3]
    if not hit:
        near = [c for c in cues if c[0] < t.end and c[1] > t.start]
        print(f"  台词 {t.start:6.2f}-{t.end:6.2f} 「{t.line.text[:14]}」 无字幕"
              + (f"  与字幕 {near[0][0]:.2f}-{near[0][1]:.2f} 重叠" if near else ""))
    else:
        c = hit[0]
        if c[1] < t.start + (t.end - t.start) * 0.85:
            print(f"  台词 {t.start:6.2f}-{t.end:6.2f} 字幕 {c[0]:.2f}-{c[1]:.2f} 提前结束")
