"""Every line has to end up in a shot, and the lines must not be stretched."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.pipeline.base import (_line_duration, _shot_line_map,
                                   SHOT_DIALOGUE_MAX)
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
for name in sys.argv[1:]:
    p = ProjectStore(Path(r"E:\dramakit\projects") / name).load()
    print(f"=== {name}")
    for sc in p.episodes[0].scenes:
        spoken = [l for l in sc.lines if not is_narration(l)]
        durs = [_line_duration(l) for l in spoken]
        m = _shot_line_map(sc.shots, len(spoken),
                           max_shot=cfg.comfyui.max_video_seconds,
                           line_durs=durs, max_dialogue=SHOT_DIALOGUE_MAX) or {}
        placed = sorted(k for v in m.values() for k in v)
        missing = [k for k in range(1, len(spoken) + 1) if k not in placed]
        dup = len(placed) != len(set(placed))
        seq = [k for sh in sc.shots for k in m.get(sh.id, [])]
        in_order = seq == sorted(seq)
        owned_total = sum(durs[k - 1] for k in placed if k - 1 < len(durs))
        need = sum(durs) + 0.35 * max(0, len(spoken) - 1)
        print(f"  场景{sc.index}: {len(spoken)} 句, {len(sc.shots)} 镜  "
              f"已分配 {len(placed)}  漏 {missing}  重复 {dup}  顺序对 {in_order}")
        print(f"        对白合计 {owned_total:.2f}s  需要(带留白) {need:.2f}s  "
              f"差额 {need-owned_total:+.2f}s")
