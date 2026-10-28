"""Budget the shots by how much dialogue there is, not by how many lines.

A scene with four long sentences needs more shots than a scene with four
short ones: at three and a half seconds a shot, eleven seconds of dialogue
cannot go into three shots. Asking for two shots and being given four
sentences is what produced the six second shots.
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\storyboard.py")
s = p.read_text(encoding="utf-8")

old = """        # every scene gets the shots its own lines need - two lines per shot
        # is the rhythm a short drama runs at
        needs = []
        for sc in ep.scenes:
            spoken = sum(1 for l in sc.lines if not is_narration(l))
            needs.append(max(cfg.min_shots_per_scene, -(-spoken // 2)))"""
new = """        # every scene gets the shots its own dialogue needs: a shot holds
        # three and a half seconds of talking, so the count comes from the
        # length of the lines and not from how many there are
        needs = []
        for sc in ep.scenes:
            spoken = [l for l in sc.lines if not is_narration(l)]
            secs = sum(estimate_reading_seconds(l.text) for l in spoken) * 1.2
            want = max(cfg.min_shots_per_scene, -(-int(secs * 100) // 3500))
            needs.append(want)"""
assert old in s, "镜头预算锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("storyboard.py 已打补丁")
