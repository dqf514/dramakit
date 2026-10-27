"""The scene has to be long enough for the lines and the breaths between them."""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\base.py")
s = p.read_text(encoding="utf-8")

old = """        raw_lines = [(_line_duration(l), l) for l in spoken]
        scene_audio = round(sum(d for d, _ in raw_lines), 3)"""
new = """        raw_lines = [(_line_duration(l), l) for l in spoken]
        gap = max(0.0, float(line_gap))
        # the scene has to hold the lines and the breaths between them
        scene_audio = round(sum(d for d, _ in raw_lines)
                            + gap * max(0, len(raw_lines) - 1), 3)"""
assert old in s, "scene_audio 锚点没找到"
s = s.replace(old, new, 1)

old = """        shot_durs: list[float] = []
        for sh in sc.shots:
            d = max(sh.duration, min_shot)
            if line_map:
                idxs = line_map.get(sh.id) or []
                owned = sum(raw_lines[i - 1][0] for i in idxs)
                if owned > 0:
                    d = owned
            shot_durs.append(d)"""
new = """        shot_durs: list[float] = []
        for sh in sc.shots:
            d = max(sh.duration, min_shot)
            if line_map:
                idxs = line_map.get(sh.id) or []
                owned = sum(raw_lines[i - 1][0] for i in idxs)
                if owned > 0:
                    d = owned + gap * max(0, len(idxs) - 1)
            shot_durs.append(d)"""
assert old in s, "shot_durs 锚点没找到"
s = s.replace(old, new, 1)

# the gap is now computed above
old = """        timed_lines: list[TimedLine] = []
        gap = max(0.0, float(line_gap))
        if line_map and timed_shots:"""
new = """        timed_lines: list[TimedLine] = []
        if line_map and timed_shots:"""
assert old in s, "gap 重复定义锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("base.py 已打补丁")
