"""A contact sheet of a finished episode - one frame per shot, tiled.

This is how the episode reads as a sequence of pictures: the cut rhythm,
whether the shots are varied, whether the framing repeats.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.media import ffmpeg as ff
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

name = sys.argv[1]
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
    rf"C:\Users\David\AppData\Local\Temp\opencode\sheet_{name}.jpg")
cfg = Config.load(r"E:\dramakit\config\default.yaml")
proj = Path(r"E:\dramakit\projects") / name
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
tl = build_timeline(ep)

tmp = Path(r"C:\Users\David\AppData\Local\Temp\opencode")
tmp.mkdir(parents=True, exist_ok=True)
frames = []
for i, ts in enumerate(tl.shots):
    at = ts.start + ts.duration * 0.45
    p = tmp / f"sheet_{name}_{i:02d}.jpg"
    ff.extract_frame(proj / "episodes" / "ep_001.mp4", p, at=at, width=320)
    if p.exists():
        frames.append(p)

cols = 4
rows = (len(frames) + cols - 1) // cols
# a concat list keeps the order, then one tile filter lays them out
lst = tmp / f"sheet_{name}.txt"
lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in frames), encoding="utf-8")
cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
       "-vf", f"scale=320:180,tile={cols}x{rows}", "-frames:v", "1", str(out)]
r = subprocess.run(cmd, capture_output=True)
print(f"{len(frames)} 个镜头 → {out}  ({out.stat().st_size if out.exists() else 0} 字节)")
if r.returncode:
    print(r.stderr.decode("utf-8", "replace")[:300])
print("镜头清单:")
for i, ts in enumerate(tl.shots):
    lines = [t.line.text for t in tl.lines
             if t.line.kind.value == "dialogue"
             and ts.start <= t.start < ts.start + ts.duration]
    print(f"  {i+1:2d}. {ts.duration:5.2f}s  {str(ts.shot.shot_type.value):<14}"
          f" {str(ts.shot.characters):<22} {ts.shot.camera_move:<4}"
          f" {' / '.join(lines)[:34]}")
