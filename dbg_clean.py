"""How many shots per episode have nobody speaking?

Those are the clips whose native audio is free of the gibberish voice -
the score can be built out of them.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
for name in sys.argv[1:]:
    store = ProjectStore(Path(r"E:\dramakit\projects") / name)
    ctx = Context(cfg, store)
    ep = ctx.target_episodes()[0]
    tl = build_timeline(ep, max_shot=cfg.comfyui.max_video_seconds)
    clean = []
    for ts in tl.shots:
        lines = [t for t in tl.lines
                 if t.line.kind.value == "dialogue"
                 and ts.start <= t.start < ts.start + ts.duration]
        if not lines:
            clean.append((ts.shot.id, round(ts.duration, 2)))
    total = sum(d for _, d in clean)
    print(f"{name}: {len(tl.shots)} 镜, 其中无人说话 {len(clean)} 个 "
          f"({total:.1f}s 干净音)  {clean}")
