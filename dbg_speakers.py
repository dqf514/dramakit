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
tl = build_timeline(ep, max_shot=cfg.comfyui.max_video_seconds,
                    line_gap=cfg.compose.line_gap)
for i, ts in enumerate(tl.shots, 1):
    lines = [t.line for t in tl.lines
             if t.line.kind.value == "dialogue"
             and ts.start - 0.02 <= t.start < ts.start + ts.duration]
    who = "、".join(sorted({l.speaker for l in lines})) or "（无人说话）"
    print(f"镜{i} {ts.start:5.1f}-{ts.start+ts.duration:5.1f}s "
          f"{ts.shot.shot_type.value:<5} 画面里：{str(ts.shot.characters):<22} 说话：{who}")
    for l in lines:
        print(f"        「{l.text[:26]}」")
