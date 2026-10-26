"""Where do the lines sit relative to the cuts?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
proj = Path(r"E:\dramakit\projects") / sys.argv[1]
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
tl = build_timeline(ep)

for si, sc in enumerate(tl.scenes):
    print(f"=== 场景 {si} 时长 {sc.duration:.2f}s ===")
    for ts in sc.shots:
        print(f"   镜 {ts.shot.id} {ts.start:6.2f}-{ts.start+ts.duration:6.2f} "
              f"({ts.duration:5.2f}s) lines={ts.shot.line_indices} "
              f"{str(ts.shot.characters):<20} 「{(ts.shot.action or '')[:26]}」")
    for t in sc.lines:
        l = t.line
        if l.kind.value != "dialogue":
            continue
        shot = next((x for x in sc.shots
                     if x.start <= t.start < x.start + x.duration), None)
        drift = t.start - shot.start if shot else -1
        print(f"   台词 {t.start:6.2f} {l.speaker:<8} 「{l.text[:20]}」 "
              f"切点漂移 {drift:5.2f}")
