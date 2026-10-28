import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.pipeline.base import (_line_duration, _shot_line_map,
                                   SHOT_DIALOGUE_MAX)
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
name = sys.argv[1]
store = ProjectStore(Path(r"E:\dramakit\projects") / name)
proj = store.load()
ep = proj.episodes[0]
for sc in ep.scenes:
    spoken = [l for l in sc.lines if not is_narration(l)]
    durs = [_line_duration(l) for l in spoken]
    m = _shot_line_map(sc.shots, len(spoken),
                       max_shot=cfg.comfyui.max_video_seconds,
                       line_durs=durs, max_dialogue=SHOT_DIALOGUE_MAX)
    print(f"=== 场景 {sc.index}: {len(spoken)} 句, {len(sc.shots)} 镜")
    for sh in sc.shots:
        idxs = (m or {}).get(sh.id, [])
        owned = sum(durs[i - 1] for i in idxs)
        flag = "  <-- 超上限" if owned > SHOT_DIALOGUE_MAX + 0.01 else ""
        print(f"   {sh.id} lines={idxs} 对白 {owned:5.2f}s{flag}")
