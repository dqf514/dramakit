"""Get the timing of the lines and the breaths between them right.

A shot that carries lines is exactly as long as those lines plus the
breaths between them, and the breath after the last line of a shot belongs
to the gap that separates it from the next one.
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\base.py")
s = p.read_text(encoding="utf-8")

old = """        shot_durs: list[float] = []
        for sh in sc.shots:
            d = max(sh.duration, min_shot)
            if line_map:
                idxs = line_map.get(sh.id) or []
                owned = sum(raw_lines[i - 1][0] for i in idxs)
                if owned > 0:
                    d = owned + gap * max(0, len(idxs) - 1)
            shot_durs.append(d)"""
new = """        # a shot with lines lasts exactly as long as those lines and the
        # breaths between them; the breath after its last line is the room
        # before the next shot starts
        line_shot_pos = [i for i, sh in enumerate(sc.shots)
                         if line_map and (line_map.get(sh.id) or [])]
        last_line_shot = line_shot_pos[-1] if line_shot_pos else -1
        shot_durs: list[float] = []
        for i, sh in enumerate(sc.shots):
            d = max(sh.duration, min_shot)
            if line_map:
                idxs = line_map.get(sh.id) or []
                owned = sum(raw_lines[i - 1][0] for i in idxs)
                if owned > 0:
                    d = owned + gap * max(0, len(idxs) - 1)
                    if i != last_line_shot:
                        d += gap
            shot_durs.append(d)"""
assert old in s, "shot_durs 锚点没找到"
s = s.replace(old, new, 1)

old = """                inner = ts.start
                total = sum(raw_lines[j - 1][0] for j in idxs)
                # the room the lines need inside this shot, gaps included
                need = total + gap * (len(idxs) - 1)
                room = max(ts.duration, need)
                for n, i in enumerate(idxs):
                    d, l = raw_lines[i - 1]
                    share = d * (room / max(total, 1e-6))
                    timed_lines.append(TimedLine(l, sc.id, round(inner, 3),
                                                 round(inner + share, 3)))
                    inner += share
                    if n < len(idxs) - 1:
                        inner += gap * (room / max(total, 1e-6))"""
new = """                inner = ts.start
                total = sum(raw_lines[j - 1][0] for j in idxs)
                gaps_total = gap * max(0, len(idxs) - 1)
                # the room the lines need inside this shot, gaps included
                need = total + gaps_total
                room = max(ts.duration, need)
                # the lines share what is left once the breaths have their room
                share_k = (room - gaps_total) / max(total, 1e-6)
                for n, i in enumerate(idxs):
                    d, l = raw_lines[i - 1]
                    share = d * share_k
                    timed_lines.append(TimedLine(l, sc.id, round(inner, 3),
                                                 round(inner + share, 3)))
                    inner += share
                    if n < len(idxs) - 1:
                        inner += gap * share_k"""
assert old in s, "台词分配锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("base.py 已打补丁")
