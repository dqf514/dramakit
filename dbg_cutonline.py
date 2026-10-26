"""Does the new 'cut on the line' timeline keep the dialogue with its shot?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
proj = Path(r"E:\dramakit\projects") / (sys.argv[1] if len(sys.argv) > 1 else "轮次01_01")
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]

# what the old timeline looked like
old = build_timeline(ep)
for sc in old.scenes:
    # assign each line to the shot that has the speaker in frame, the way the
    # storyboard model is asked to do it
    spoken = [t for t in sc.lines if t.line.kind.value == "dialogue"]
    for ts in sc.shots:
        ts.shot.line_indices = []
    for k, t in enumerate(spoken):
        cands = [ts for ts in sc.shots if t.line.speaker in (ts.shot.characters or [])]
        if not cands:
            continue
        # the shot whose place in the list is closest to the line's order
        want = (k + 1) / max(len(spoken), 1) * len(sc.shots)
        best = min(cands, key=lambda ts: abs(ts.shot.index - want))
        best.shot.line_indices.append(k + 1)

new = build_timeline(ep)
print(f"场景数 {len(new.scenes)}  总长 {old.duration:.2f}s -> {new.duration:.2f}s")
bad = 0
for si, sc in enumerate(new.scenes):
    print(f"=== 场景 {si} 时长 {sc.duration:.2f}s ===")
    for ts in sc.shots:
        print(f"   {ts.start:6.2f}-{ts.start+ts.duration:6.2f} "
              f"({ts.duration:5.2f}s) {str(ts.shot.characters):<20} "
              f"lines={ts.shot.line_indices}")
    for t in sc.lines:
        l = t.line
        if l.kind.value != "dialogue":
            continue
        shot = next((x for x in sc.shots
                     if x.start <= t.start < x.start + x.duration), None)
        on = shot.shot.characters if shot else []
        mark = ""
        if on and l.speaker not in on:
            mark = "   <-- 说话时镜头里是别人"
            bad += 1
        print(f"   台词 {t.start:6.2f}-{t.end:6.2f} {l.speaker:<8} 「{l.text[:18]}」"
              f"   镜头 {str(on):<18}{mark}")
print(f"\n说话时镜头里是别人的台词: {bad} 句")
