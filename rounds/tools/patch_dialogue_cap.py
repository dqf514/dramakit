"""Apply the dialogue limit to the fallback and to the leftover lines."""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\base.py")
s = p.read_text(encoding="utf-8")

# 1) the leftover lines respect the same limit
old = """            fits = [sh for sh in shots
                    if not (max_shot > 0 and length_of(sh.id) + d > max_shot)]"""
new = """            fits = [sh for sh in shots
                    if not (limit > 0 and length_of(sh.id) + d > limit)]"""
assert old in s, "fits 锚点没找到"
s = s.replace(old, new, 1)

# 2) the fallback assignment respects it too
old = """def _assign_by_cast(shots, line_durs: list[float],
                    speakers: list[str],
                    max_shot: float = 0.0) -> dict[str, list[int]] | None:"""
new = """def _assign_by_cast(shots, line_durs: list[float],
                    speakers: list[str],
                    max_shot: float = 0.0,
                    max_dialogue: float = 0.0) -> dict[str, list[int]] | None:"""
assert old in s, "_assign_by_cast 签名锚点没找到"
s = s.replace(old, new, 1)

old = """    if not shots or not speakers:
        return None
    n = len(speakers)
    claimed: dict[str, list[int]] = {}

    def length_of(sid: str) -> float:
        return sum(line_durs[i - 1] for i in claimed.get(sid, []))
"""
new = """    if not shots or not speakers:
        return None
    n = len(speakers)
    claimed: dict[str, list[int]] = {}
    limit = max_shot if max_shot > 0 else 0.0
    if max_dialogue > 0:
        limit = max_dialogue if limit <= 0 else min(limit, max_dialogue)

    def length_of(sid: str) -> float:
        return sum(line_durs[i - 1] for i in claimed.get(sid, []))
"""
assert old in s, "length_of 锚点没找到"
s = s.replace(old, new, 1)

s = s.replace("""                 and not (max_shot > 0 and length_of(sh.id) + d > max_shot)]""",
              """                 and not (limit > 0 and length_of(sh.id) + d > limit)]""")
s = s.replace("""                and not (max_shot > 0 and length_of(sh.id) + d > max_shot)]""",
              """                and not (limit > 0 and length_of(sh.id) + d > limit)]""")

# 3) the timeline passes the limit down
old = """        line_map = _shot_line_map(sc.shots, len(raw_lines), max_shot=max_shot,
                                   line_durs=[d for d, _ in raw_lines])"""
new = """        line_map = _shot_line_map(sc.shots, len(raw_lines), max_shot=max_shot,
                                   line_durs=[d for d, _ in raw_lines],
                                   max_dialogue=SHOT_DIALOGUE_MAX)"""
assert old in s, "line_map 调用锚点没找到"
s = s.replace(old, new, 1)

old = """            line_map = _assign_by_cast(sc.shots, [d for d, _ in raw_lines],
                                       [l.speaker for _, l in raw_lines],
                                       max_shot=max_shot)"""
new = """            line_map = _assign_by_cast(sc.shots, [d for d, _ in raw_lines],
                                       [l.speaker for _, l in raw_lines],
                                       max_shot=max_shot,
                                       max_dialogue=SHOT_DIALOGUE_MAX)"""
assert old in s, "_assign_by_cast 调用锚点没找到"
s = s.replace(old, new, 1)

# 4) the constant
old = """def _line_duration(line: Line) -> float:"""
new = """# a shot carries at most this much dialogue: a short drama cuts fast
SHOT_DIALOGUE_MAX = 5.5


def _line_duration(line: Line) -> float:"""
assert old in s, "_line_duration 锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("base.py 已打补丁")
