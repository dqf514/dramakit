"""The line map with the real durations, next to the one with made-up ones."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, _shot_line_map
from dramakit.models import is_narration
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\\tmp\\ep23")
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 2
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.project.episode(ep_index)
print("max_video_seconds =", cfg.comfyui.max_video_seconds)

for sc in ep.scenes:
    spoken = [l for l in sc.lines if not is_narration(l)]
    durs = [float(l.duration or 2.0) for l in spoken]
    real = _shot_line_map(sc.shots, len(spoken), max_shot=cfg.comfyui.max_video_seconds,
                         line_durs=durs, max_dialogue=4.5,
                         speakers=[l.speaker for l in spoken])
    fake = _shot_line_map(sc.shots, len(spoken), max_shot=15.0,
                          line_durs=[2.0] * len(spoken), max_dialogue=4.5,
                          speakers=[l.speaker for l in spoken])
    if real == fake:
        continue
    print("=" * 60)
    print("台词:", [(i + 1, l.speaker, l.text[:10], round(d, 1))
                  for i, (l, d) in enumerate(zip(spoken, durs))])
    for sh in sc.shots:
        r = sorted((real or {}).get(sh.id) or [])
        f = sorted((fake or {}).get(sh.id) or [])
        mark = "  " if r == f else "≠ "
        print(f"  {mark}{sh.id[:14]} 分镜表={sh.line_indices} 真={r} 假={f}")
