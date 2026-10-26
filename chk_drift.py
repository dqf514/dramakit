import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import build_timeline
from dramakit.project import ProjectStore
from dramakit.media import ffmpeg as ff

cfg = Config.load(r"E:\dramakit\config\default.yaml")
root = Path(r"E:\dramakit\projects\测试短剧")
store = ProjectStore(root)
proj = store.load()

worst = 0
for ep in proj.episodes:
    tl = build_timeline(ep)
    for ts in tl.shots:
        vp = ts.shot.video_path
        if not vp:
            continue
        d = ff.probe_duration(store.abs(vp))
        gap = ts.duration - d
        worst = max(worst, abs(gap))
        flag = "  <-- 差得多" if abs(gap) > 0.6 else ""
        print(f"  {ts.shot.id[:14]:16s} 槽位 {ts.duration:5.2f}s  视频 {d:5.2f}s  "
              f"差 {gap:+5.2f}s{flag}")
print(f"\n最大偏差 {worst:.2f}s")
