"""What durations do the shots actually need?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
root = Path(r"E:\dramakit\projects\测试短剧")
store = ProjectStore(root)
proj = store.load()

for ep in proj.episodes:
    tl = build_timeline(ep)
    print(f"=== 第{ep.index}集 总时长 {tl.duration:.1f}s / {len(tl.shots)} 镜")
    for ts in tl.shots:
        d = ts.duration
        loop = "循环" if d > 5.17 else ("裁切" if d < 5.0 else "刚好")
        print(f"   {ts.shot.id} {d:6.2f}s  ({loop})")
