"""Does the generated video drift away from its first frame?

The first frame is what FLUX 3 drew; the video is what H3 made out of it.
If the character deforms or the scene changes while the shot plays, the
episode falls apart on screen.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.media import ffmpeg as ff
from dramakit.media import grade as gr
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
name = sys.argv[1]
proj = Path(r"E:\dramakit\projects") / name
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
tl = build_timeline(ep)
tmp = Path(r"C:\Users\David\AppData\Local\Temp\opencode")
tmp.mkdir(parents=True, exist_ok=True)

for ts in tl.shots:
    sh = ts.shot
    if not sh.video_path:
        continue
    vp = store.abs(sh.video_path)
    if not vp.exists():
        continue
    dur = ff.probe_duration(vp)
    if dur < 0.5:
        continue
    first = tmp / f"drift_{sh.id}_a.png"
    mid = tmp / f"drift_{sh.id}_b.png"
    ff.extract_frame(vp, first, at=0.05, width=480)
    ff.extract_frame(vp, mid, at=max(dur * 0.75, 0.1), width=480)
    if not (first.exists() and mid.exists()):
        continue
    a, b = gr.analyze(first), gr.analyze(mid)
    # how much the picture moved: mean absolute luma difference
    drift = abs(a.luma - b.luma)
    print(f"{sh.id} {dur:5.2f}s  首帧亮度 {a.luma:6.1f}  片中 {b.luma:6.1f}  "
          f"差 {drift:5.1f}  饱和 {a.sat:4.1f}->{b.sat:4.1f}")
