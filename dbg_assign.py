import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.pipeline.base import Context, _assign_by_cast, _line_duration
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
name = sys.argv[1]
store = ProjectStore(Path(r"E:\dramakit\projects") / name)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
cap = cfg.comfyui.max_video_seconds
for sc in ep.scenes:
    spoken = [l for l in sc.lines if not is_narration(l)]
    durs = [_line_duration(l) for l in spoken]
    m = _assign_by_cast(sc.shots, durs, [l.speaker for l in spoken], max_shot=cap)
    print(f"场景 {sc.index}: {len(spoken)} 句, {len(sc.shots)} 镜")
    for sh in sc.shots:
        idxs = (m or {}).get(sh.id, [])
        tot = sum(durs[i - 1] for i in idxs)
        print(f"   {sh.id} lines={idxs} 共 {tot:5.2f}s"
              f"{'   <-- 超过上限' if tot > cap else ''}")
