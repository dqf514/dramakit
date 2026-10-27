import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
store = ProjectStore(Path(r"E:\dramakit\projects") / (sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"))
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
tl = build_timeline(ep, max_shot=cfg.comfyui.max_video_seconds,
                    line_gap=cfg.compose.line_gap)
for sc in tl.scenes:
    print(f"=== 场景 {sc.scene.index} {sc.duration:.2f}s")
    for ts in sc.shots:
        print(f"  镜 {ts.start:6.2f}-{ts.start+ts.duration:6.2f} ({ts.duration:5.2f}s)"
              f"  lines={ts.shot.line_indices}")
    for t in sc.lines:
        if t.line.kind.value != "dialogue":
            continue
        shot = next((x for x in sc.shots
                     if x.start - 0.02 <= t.start < x.start + x.duration), None)
        over = ""
        if shot:
            over = f"  (镜头到 {shot.start+shot.duration:.2f} 结束)"
        print(f"  台词 {t.start:6.2f}-{t.end:6.2f} 「{t.line.text[:14]}」{over}")
