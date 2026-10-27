import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.pipeline.base import Context, _line_duration
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
name = sys.argv[1]
si = int(sys.argv[2]) if len(sys.argv) > 2 else None
store = ProjectStore(Path(r"E:\dramakit\projects") / name)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
for sc in ep.scenes:
    if si is not None and sc.index != si:
        continue
    print(f"场景 {sc.index}:")
    for l in sc.lines:
        if is_narration(l):
            continue
        print(f"   {_line_duration(l):5.2f}s ({len(l.text):2d}字) {l.speaker[:6]:6s} "
              f"「{l.text[:38]}」")
