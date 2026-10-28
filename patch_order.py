"""The shots have to carry the lines in the order they are spoken.

A storyboard sometimes hands a later line to an earlier shot. The
timeline places the lines inside their shots, so the scene would be played
back with the dialogue out of order - the audience hears the answer
before the question. When the assignment is not in order, the lines are
handed out in order instead, using the storyboard's counts.
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\base.py")
s = p.read_text(encoding="utf-8")

old = """    for sid in claimed:
        claimed[sid].sort()
    return claimed


def _assign_by_cast("""
new = """    for sid in claimed:
        claimed[sid].sort()

    # the lines have to come out in the order they were written
    seq: list[int] = []
    for sh in shots:
        seq += claimed.get(sh.id, [])
    if seq != sorted(seq):
        counts = [len(claimed.get(sh.id, [])) for sh in shots]
        claimed = {}
        nxt = 1
        for sh, n in zip(shots, counts):
            if n <= 0:
                continue
            take = [k for k in range(nxt, min(nxt + n, n_lines + 1))]
            if take:
                claimed[sh.id] = take
                nxt = take[-1] + 1
        # anything the storyboard did not place goes to the last shot that
        # still has room, in order
        left = [k for k in range(1, n_lines + 1) if k not in seq]
        if left:
            for sh in shots:
                if len(claimed.get(sh.id, [])) >= 2:
                    continue
                claimed.setdefault(sh.id, []).append(left.pop(0))
                if not left:
                    break
        for sid in claimed:
            claimed[sid].sort()
    return claimed


def _assign_by_cast("""
assert old in s, "claimed 收尾锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("base.py 已打补丁")
