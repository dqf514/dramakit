"""Give every scene a fair share of the episode's shot budget.

The first scene used to take whatever was left and leave the last scene
with two shots for six lines - the lines then had to share shots, and the
picture stopped following the dialogue.
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\storyboard.py")
s = p.read_text(encoding="utf-8")

old = """        for sc in ep.scenes:
            if sc.shots:
                continue
            narration_sec = round(sum(estimate_reading_seconds(l.text) for l in sc.lines), 1)"""
new = """        # every scene gets the shots its own lines need - two lines per shot
        # is the rhythm a short drama runs at
        needs = []
        for sc in ep.scenes:
            spoken = sum(1 for l in sc.lines if not is_narration(l))
            needs.append(max(cfg.min_shots_per_scene, -(-spoken // 2)))
        total_need = sum(needs)
        budget = max(cfg.max_shots_per_episode, total_need)
        for sc, need in zip(ep.scenes, needs):
            if sc.shots:
                continue
            share = max(cfg.min_shots_per_scene,
                        -(-need * budget // max(total_need, 1)))
            sc._shot_budget = share        # type: ignore[attr-defined]

        for sc in ep.scenes:
            if sc.shots:
                continue
            narration_sec = round(sum(estimate_reading_seconds(l.text) for l in sc.lines), 1)"""
assert old in s, "场景循环锚点没找到"
s = s.replace(old, new, 1)

old = """            left = max(cfg.min_shots_per_scene,
                       cfg.max_shots_per_episode - sum(len(s.shots) for s in ep.scenes))
            max_shots = max(cfg.min_shots_per_scene,
                            min(cfg.max_shots_per_scene, left))"""
new = """            left = max(cfg.min_shots_per_scene,
                       cfg.max_shots_per_episode - sum(len(s.shots) for s in ep.scenes))
            want = getattr(sc, "_shot_budget", 0)
            max_shots = max(cfg.min_shots_per_scene,
                            min(cfg.max_shots_per_scene, left, want) if want
                            else min(cfg.max_shots_per_scene, left))"""
assert old in s, "镜头预算锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("storyboard.py 已打补丁")
