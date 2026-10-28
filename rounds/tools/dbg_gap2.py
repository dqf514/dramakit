import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.pipeline.base import Context, _line_duration, _shot_line_map, SHOT_DIALOGUE_MAX
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
store = ProjectStore(Path(r"E:\dramakit\projects") / "轮次09_09")
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
gap = cfg.compose.line_gap

for sc in ep.scenes:
    spoken = [l for l in sc.lines if not is_narration(l)]
    raw = [(_line_duration(l), l) for l in spoken]
    lm = _shot_line_map(sc.shots, len(raw), max_shot=cfg.comfyui.max_video_seconds,
                        line_durs=[d for d, _ in raw], max_dialogue=SHOT_DIALOGUE_MAX)
    scene_audio = round(sum(d for d, _ in raw) + gap * max(0, len(raw) - 1), 3)
    durs = []
    for sh in sc.shots:
        d = max(sh.duration, 1.0)
        if lm:
            idxs = lm.get(sh.id) or []
            owned = sum(raw[i - 1][0] for i in idxs)
            if owned > 0:
                d = owned + gap * max(0, len(idxs) - 1)
        durs.append(d)
    shot_sum = round(sum(durs), 3)
    scene_dur = max(scene_audio, shot_sum, 1.0)
    print(f"场景 {sc.index}: 行数 {len(raw)} 台词总长 {sum(d for d,_ in raw):.2f} "
          f"scene_audio {scene_audio:.2f} shot_sum {shot_sum:.2f} "
          f"scene_dur {scene_dur:.2f} scale {scene_dur/shot_sum:.3f}")
    for sh, d in zip(sc.shots, durs):
        idxs = (lm or {}).get(sh.id) or []
        owned = sum(raw[i - 1][0] for i in idxs)
        need = owned + gap * max(0, len(idxs) - 1)
        print(f"   {sh.id} lines={idxs} owned={owned:.2f} need={need:.2f} "
              f"d={d:.2f} -> 实际 {d*(scene_dur/shot_sum):.2f}")
