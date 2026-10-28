import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, build_timeline, _line_duration
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
name = sys.argv[1]
store = ProjectStore(Path(r"E:\dramakit\projects") / name)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]

print("台词原始数据:")
for sc in ep.scenes:
    for l in sc.lines:
        if l.kind.value != "dialogue":
            continue
        d = _line_duration(l)
        print(f"  {l.id} dur字段={l.duration:6.3f} 估算={d:6.3f} "
              f"音频={Path(l.audio_path).name if l.audio_path else '(无)'} 「{l.text[:14]}」")

print()
tl = build_timeline(ep, max_shot=cfg.comfyui.max_video_seconds,
                    line_gap=cfg.compose.line_gap)
print("时间线:")
for t in tl.lines[:10]:
    print(f"  {t.start:6.2f}-{t.end:6.2f} 「{t.line.text[:14]}」")
