"""The timed lines of a scene, with the shot windows they fall into."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\\tmp\\ep23")
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 2
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.project.episode(ep_index)
tl = ctx.timeline(ep)

for tsc in tl.scenes:
    print("=" * 60)
    for ts in tsc.shots:
        print(f"  镜头 {ts.shot.id[:14]} [{ts.start:7.2f},{ts.start+ts.duration:7.2f}]")
    for t in tsc.lines:
        where = [ts.shot.id[:12] for ts in tsc.shots
                 if ts.start <= t.start < ts.start + ts.duration]
        print(f"  台词 {t.start:7.2f}-{t.end:7.2f} 「{t.line.text[:16]}」 "
              f"落在 {where or '（不在任何镜头里）'}")
