"""Leave room between the lines.

Lines that run into each other sound like someone reading a list. A short
drama needs the half second after a line where the other person takes it in
- that silence is where the tension lives.
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\base.py")
s = p.read_text(encoding="utf-8")

old = """def build_timeline(ep: Episode, min_shot: float = 1.0,
                   max_shot: float = 0.0) -> Timeline:"""
new = """def build_timeline(ep: Episode, min_shot: float = 1.0,
                   max_shot: float = 0.0, line_gap: float = 0.0) -> Timeline:"""
assert old in s, "签名锚点没找到"
s = s.replace(old, new, 1)

old = """        # 4) place the spoken lines: inside the shot that carries them, one
        #    after another, so the picture and the dialogue stay together
        timed_lines: list[TimedLine] = []
        if line_map and timed_shots:
            by_shot: dict[str, list[int]] = line_map
            for ts in timed_shots:
                idxs = sorted(by_shot.get(ts.shot.id) or [])
                inner = ts.start
                for i in idxs:
                    d, l = raw_lines[i - 1]
                    share = d * (ts.duration / max(
                        sum(raw_lines[j - 1][0] for j in idxs), 1e-6))
                    timed_lines.append(TimedLine(l, sc.id, round(inner, 3),
                                                 round(inner + share, 3)))
                    inner += share
        else:
            line_cursor = cursor
            for d, l in raw_lines:
                timed_lines.append(TimedLine(l, sc.id, round(line_cursor, 3),
                                             round(line_cursor + d, 3)))
                line_cursor += d"""
new = """        # 4) place the spoken lines: inside the shot that carries them, one
        #    after another, so the picture and the dialogue stay together.
        #    A short breath between the lines: lines that run into each
        #    other sound like a list being read out.
        timed_lines: list[TimedLine] = []
        gap = max(0.0, float(line_gap))
        if line_map and timed_shots:
            by_shot: dict[str, list[int]] = line_map
            for ts in timed_shots:
                idxs = sorted(by_shot.get(ts.shot.id) or [])
                if not idxs:
                    continue
                inner = ts.start
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
                        inner += gap * (room / max(total, 1e-6))
        else:
            line_cursor = cursor
            for n, (d, l) in enumerate(raw_lines):
                timed_lines.append(TimedLine(l, sc.id, round(line_cursor, 3),
                                             round(line_cursor + d, 3)))
                line_cursor += d
                if n < len(raw_lines) - 1:
                    line_cursor += gap"""
assert old in s, "台词放置锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("base.py 已打补丁")
