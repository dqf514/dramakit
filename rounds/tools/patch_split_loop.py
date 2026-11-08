"""A split that does not split anything is not a split.

A line longer than the limit on its own made the split take nothing
(`keep` was zero), so the second half was given all of the lines and
the loop came straight back to it - and came back again, and each time
the second half's description grew by three characters ("接上："), until
the machine ran out of memory in the middle of a scene.

So: the first line always stays with its shot, however long it is, and
the "接上：" chain never piles up.
"""
import pathlib
import re

P = pathlib.Path(r"E:\dramakit\dramakit\pipeline\storyboard.py")
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

# ---- 1. the first line stays with its shot ------------------------------ #
old = """        if keep >= len(idxs):
            i += 1
            continue
        moved = idxs[keep:]"""
new = """        # A line can be longer than the limit on its own.  It still has
        # to live somewhere, so the shot keeps it - and the split stops
        # here.  Without that, the second half is given all of the lines
        # and the loop comes straight back to it, over and over.
        if keep == 0:
            keep = 1
        if keep >= len(idxs):
            i += 1
            continue
        moved = idxs[keep:]"""
assert old in text
text = text.replace(old, new, 1)

# ---- 2. the "接上：" chain does not pile up ----------------------------- #
old = """            action=(f"接上：{tail}" if tail else f"接上：{shot.action or ''}"),"""
new = """            action=(f"接上：{tail}" if tail
                    else f"接上：{_strip_prefix(shot.action or '')}"),"""
assert old in text
text = text.replace(old, new, 1)

# the helper, next to the other action helpers
old = """def _split_long_shots(sc, max_dialogue: float = SHOT_DIALOGUE_MAX) -> int:"""
new = '''_PREFIX_RE = re.compile(r"^(?:接上[：:]\\s*)+")


def _strip_prefix(action: str) -> str:
    """Take off the "接上：" that a previous split put on.

    The second half of a split continues the first, so it says so.  But
    a shot that is split again would say it twice, and again, and the
    description would be nothing but "接上：".
    """
    return _PREFIX_RE.sub("", action or "").strip()


def _split_long_shots(sc, max_dialogue: float = SHOT_DIALOGUE_MAX) -> int:'''
assert old in text
text = text.replace(old, new, 1)

# ---- 3. a scene cannot be split forever --------------------------------- #
old = """    added = 0
    i = 0
    while i < len(sc.shots):"""
new = """    added = 0
    i = 0
    # a split that does not stop is a loop that eats the machine
    guard = 4 * (len(sc.shots) + len(spoken)) + 20
    while i < len(sc.shots) and guard > 0:
        guard -= 1"""
assert old in text
text = text.replace(old, new, 1)

if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("拆分的死循环修好了")
