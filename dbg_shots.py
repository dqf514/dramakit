"""Shot list and line list of an episode, side by side."""
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
    print(f"=== 场景 {si}  时长 {sc.duration:.2f}s ===")
    print("镜头:")
    for ts in sc.shots:
        print(f"   {ts.start:6.2f}-{ts.start+ts.duration:6.2f}  "
              f"{str(ts.shot.characters):<22} {ts.shot.shot_type:<6} "
              f"{ts.shot.duration:.2f}s  「{(ts.shot.action or '')[:26]}」")
    print("台词:")
    for t in sc.lines:
        l = t.line
        if l.kind.value != "dialogue":
            print(f"   {t.start:6.2f}-{t.end:6.2f}  [{l.kind.value}] 「{l.text[:24]}」")
            continue
        shot = next((x for x in sc.shots
                     if x.start <= t.start < x.start + x.duration), None)
        on = shot.shot.characters if shot else []
        mark = "" if (not on or l.speaker in on) else "   <-- 说话时镜头里是别人"
        print(f"   {t.start:6.2f}-{t.end:6.2f}  {l.speaker:<8} 「{l.text[:22]}」"
              f"   镜头: {str(on):<20}{mark}")
