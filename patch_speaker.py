"""A line goes to a shot that has the speaker in frame.

The storyboard's assignment is a hint. What matters is that the person
whose voice you hear is the one on camera: a line about the ring dropped
onto a close-up of the man means the viewer hears the woman and watches the
man talk.
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\base.py")
s = p.read_text(encoding="utf-8")

# 1) the helper that knows who is in a shot
old = """def _shot_line_map(shots, n_lines: int, max_shot: float = 0.0,
                   line_durs: list[float] | None = None,
                   max_dialogue: float = 0.0) -> dict[str, list[int]] | None:"""
new = """def _shot_line_map(shots, n_lines: int, max_shot: float = 0.0,
                   line_durs: list[float] | None = None,
                   max_dialogue: float = 0.0,
                   speakers: list[str] | None = None) -> dict[str, list[int]] | None:"""
assert old in s, "签名锚点没找到"
s = s.replace(old, new, 1)

# 2) a shot only keeps a line if the speaker is in it
old = """    claimed: dict[str, list[int]] = {}
    used: set[int] = set()
    for sh in shots:
        idxs = []
        for n in sh.line_indices:
            if 1 <= n <= n_lines and n not in used:
                idxs.append(n)
                used.add(n)"""
new = """    claimed: dict[str, list[int]] = {}
    used: set[int] = set()
    for sh in shots:
        idxs = []
        for n in sh.line_indices:
            if 1 <= n <= n_lines and n not in used:
                if speakers is not None:
                    spk = speakers[n - 1] if n - 1 < len(speakers) else ""
                    if spk and sh.characters and spk not in sh.characters:
                        # the speaker is not in this shot: the line goes
                        # somewhere he can be seen
                        continue
                idxs.append(n)
                used.add(n)"""
assert old in s, "主循环锚点没找到"
s = s.replace(old, new, 1)

# 3) the leftovers prefer the shots the speaker is in
old = """            fits = [sh for sh in shots
                    if not (limit > 0 and length_of(sh.id) + d > limit)]
            empty = [sh for sh in fits if not claimed.get(sh.id)]"""
new = """            fits = [sh for sh in shots
                    if not (limit > 0 and length_of(sh.id) + d > limit)]
            if speakers is not None:
                spk = speakers[n - 1] if n - 1 < len(speakers) else ""
                with_speaker = [sh for sh in fits
                                if spk and spk in (sh.characters or [])]
                if with_speaker:
                    fits = with_speaker
            empty = [sh for sh in fits if not claimed.get(sh.id)]"""
assert old in s, "补位锚点没找到"
s = s.replace(old, new, 1)

# 4) the timeline passes the speakers in
old = """        line_map = _shot_line_map(sc.shots, len(raw_lines), max_shot=max_shot,
                                   line_durs=[d for d, _ in raw_lines],
                                   max_dialogue=SHOT_DIALOGUE_MAX)"""
new = """        line_map = _shot_line_map(sc.shots, len(raw_lines), max_shot=max_shot,
                                   line_durs=[d for d, _ in raw_lines],
                                   max_dialogue=SHOT_DIALOGUE_MAX,
                                   speakers=[l.speaker for _, l in raw_lines])"""
assert old in s, "时间线调用锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("base.py 已打补丁")
