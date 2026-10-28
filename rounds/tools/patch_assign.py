"""The storyboard decides who says what in which shot; the timeline obeys.

The bug this fixes: the timeline used to take a line away from its shot
when the shot carried more dialogue than the cut allowed, and hand it to
another shot. That shuffled the whole scene along by one line - the viewer
heard the woman over the man's close-up, and the answer came before the
question.

Now the storyboard's assignment is final. The length limit only steers a
line that belongs to no shot at all: it goes to a shot that has the speaker
in it, as late as possible, and never in front of the lines that are
already placed.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\base.py")
s = p.read_text(encoding="utf-8")

start = s.index("def _shot_line_map(")
end = s.index("def _assign_by_cast(")
old = s[start:end]

new = '''def _shot_line_map(shots, n_lines: int, max_shot: float = 0.0,
                   line_durs: list[float] | None = None,
                   max_dialogue: float = 0.0,
                   speakers: list[str] | None = None) -> dict[str, list[int]] | None:
    """Which lines each shot carries.

    The storyboard says which shot covers which line, and that is the
    decision: the camera is on the person who is talking. The timeline adds
    two guards.

    - A line is never taken away from the shot the storyboard gave it to.
      Taking one used to shuffle the dialogue along and put one character's
      words over another character's face.
    - A line that belongs to no shot is handed to a shot that has the
      speaker in it, as late as possible, and never in front of the lines
      that were already placed.

    A shot lasts as long as the lines it carries plus the breaths between
    them. The length limit only steers a line that has no home yet: how
    long a storyboard's own shot is, is the storyboard's business.
    """
    if not shots or n_lines <= 0:
        return None
    durs = line_durs or []
    limit = max_shot if max_shot > 0 else 0.0
    if max_dialogue > 0:
        limit = max_dialogue if limit <= 0 else min(limit, max_dialogue)

    def dur_of(n: int) -> float:
        return durs[n - 1] if n - 1 < len(durs) else 0.0

    def spk_of(n: int) -> str:
        if not speakers or n - 1 >= len(speakers):
            return ""
        return speakers[n - 1] or ""

    # 1) the storyboard's own assignment - kept as it is
    claimed: dict[str, list[int]] = {}
    used: set[int] = set()
    for sh in shots:
        idxs = [n for n in sh.line_indices if 1 <= n <= n_lines and n not in used]
        if idxs:
            claimed[sh.id] = idxs
            used.update(idxs)
    if not claimed:
        return None

    def length_of(sid: str) -> float:
        return sum(dur_of(n) for n in claimed.get(sid, []))

    def has_speaker(sh, spk: str) -> bool:
        """True when the shot can show this person talking."""
        if not spk or not sh.characters:
            return True
        return spk in sh.characters

    # 2) the lines that belong to no shot
    missing = [n for n in range(1, n_lines + 1) if n not in used]
    for n in missing:
        d = dur_of(n)
        spk = spk_of(n)
        # the shot it belongs after: the last one carrying a smaller line
        after = -1
        before = len(shots)
        for i, sh in enumerate(shots):
            for ln in claimed.get(sh.id, []):
                if ln < n:
                    after = max(after, i)
                elif ln > n:
                    before = min(before, i)
        # a shot may only take the line if it does not already carry a later
        # one - the dialogue has to come out in order
        window = [i for i in range(max(0, after), min(len(shots), max(before, after + 1)))
                  if not any(ln > n for ln in claimed.get(shots[i].id, []))]
        if not window:
            window = [max(0, min(after, len(shots) - 1))]
        cands = [shots[i] for i in window
                 if has_speaker(shots[i], spk)
                 and not (limit > 0 and length_of(shots[i].id) + d > limit)]
        if not cands:
            cands = [shots[i] for i in window if has_speaker(shots[i], spk)]
        if not cands:
            cands = [shots[i] for i in window]
        # an empty shot first, then the one closest to where the line sits
        cands.sort(key=lambda sh: (len(claimed.get(sh.id, [])), abs(sh.index - after)))
        best = cands[0]
        claimed.setdefault(best.id, []).append(n)
        used.add(n)

    for sid in claimed:
        claimed[sid].sort()
    return claimed


'''

s = s[:start] + new + s[end:]
p.write_text(s, encoding="utf-8")
print("base.py 已重写 _shot_line_map")
