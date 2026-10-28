import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
name = sys.argv[1]
store = ProjectStore(Path(r"E:\dramakit\projects") / name)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
for sc in ep.scenes:
    n = len([l for l in sc.lines if l.kind.value == "dialogue"])
    print(f"场景 {sc.index}: {n} 句台词, {len(sc.shots)} 个镜头")
    for sh in sc.shots:
        print(f"    {sh.id} 分镜时长 {sh.duration:5.2f}s  「{(sh.action or '')[:34]}」")
tl = build_timeline(ep, max_shot=cfg.comfyui.max_video_seconds)
print("时间线:")
for sc in tl.scenes:
    print(f"  场景 {sc.scene.index} 时长 {sc.duration:.2f}s")
    for ts in sc.shots:
        print(f"    {ts.shot.id} {ts.start:6.2f}-{ts.start+ts.duration:6.2f} "
              f"({ts.duration:5.2f}s)")
