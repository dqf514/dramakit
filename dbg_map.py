import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.pipeline.base import (_line_duration, _shot_line_map,
                                   SHOT_DIALOGUE_MAX)
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
p = ProjectStore(Path(r"E:\dramakit\projects\轮次06_06")).load()
sc = p.episodes[0].scenes[0]
spoken = [l for l in sc.lines if not is_narration(l)]
durs = [_line_duration(l) for l in spoken]
m = _shot_line_map(sc.shots, len(spoken),
                   max_shot=cfg.comfyui.max_video_seconds,
                   line_durs=durs, max_dialogue=SHOT_DIALOGUE_MAX) or {}
print("镜头顺序与分到的台词:")
for sh in sc.shots:
    print(f"   idx={sh.index} {sh.id} lines={m.get(sh.id, [])} "
          f"分镜原分配={sh.line_indices}")
seq = [k for sh in sc.shots for k in m.get(sh.id, [])]
print("拼接顺序:", seq, " 有序:", seq == sorted(seq))
print("台词时长:", [round(d, 2) for d in durs])
