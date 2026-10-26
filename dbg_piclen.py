"""Where does the picture lose time? clip by clip."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.media import ffmpeg as ff
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

name = sys.argv[1]
cfg = Config.load(r"E:\dramakit\config\default.yaml")
proj = Path(r"E:\dramakit\projects") / name
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
tl = build_timeline(ep)
tmp = proj / "tmp" / "ep_001"

tot_real = tot_want = 0.0
for ts in tl.shots:
    c = tmp / f"shot_{tl.shots.index(ts):04d}.mp4"
    real = ff.probe_duration(c) if c.exists() else 0.0
    tot_real += real
    tot_want += ts.duration
    mark = "  <-- 短" if real < ts.duration - 0.02 else ""
    print(f"  {ts.shot.id} 要 {ts.duration:6.3f}s  实际 {real:6.3f}s  "
          f"差 {real-ts.duration:+6.3f}{mark}")
print(f"  镜头合计: 要 {tot_want:.3f}s  实际 {tot_real:.3f}s  差 {tot_real-tot_want:+.3f}s")

for si, s in enumerate(tl.scenes):
    f = tmp / f"scene_{si:03d}_v.mp4"
    print(f"  场景 {si} 时间线 {s.duration:.3f}s  画面 "
          f"{ff.probe_duration(f) if f.exists() else 0:.3f}s")
pic = tmp / "picture.mp4"
print(f"  picture.mp4 {ff.probe_duration(pic):.3f}s   时间线 {tl.duration:.3f}s")
