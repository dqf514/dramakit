"""How long are the generated videos, and do they fill their slot?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.media import ffmpeg as ff
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
proj = Path(r"E:\dramakit\projects") / sys.argv[1]
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
tl = build_timeline(ep)

print(f"{'镜头':<14}{'槽位':>7}{'素材':>8}{'差':>8}   帧数")
short = 0
for ts in tl.shots:
    sh = ts.shot
    if not sh.video_path:
        continue
    vp = store.abs(sh.video_path)
    if not vp.exists():
        continue
    real = ff.probe_duration(vp)
    d = real - ts.duration
    flag = ""
    if d < -0.35:
        flag = "  <-- 素材比槽位短（要冻帧）"
        short += 1
    elif d > 0.6:
        flag = "  <-- 素材比槽位长（要剪掉）"
    print(f"{sh.id:<14}{ts.duration:7.2f}{real:8.2f}{d:+8.2f}{flag}")
print(f"\n素材短于槽位的镜头: {short} 个")
