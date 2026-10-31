"""The line map of a scene, next to the storyboard's assignment."""
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

for sc in ep.scenes:
    spoken = [l for l in sc.lines if not is_narration(l)]
    raw = [l for l in spoken]
    m = _shot_line_map(sc.shots, len(raw), max_shot=15.0,
                      line_durs=[2.0] * len(raw), max_dialogue=4.5,
                      speakers=[l.speaker for l in raw])
    print("=" * 60)
    print("场景台词:", [(i + 1, l.speaker, l.text[:12]) for i, l in enumerate(spoken)])
    for sh in sc.shots:
        print(f"  {sh.id[:14]} 分镜表={sh.line_indices}  "
              f"时间线分配={sorted((m or {}).get(sh.id) or [])}")
