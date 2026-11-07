"""Two shots that are the same picture are one shot.

The model sometimes wants to give the next line its own shot and does
not know what else to film, so it copies the shot before it: the same
words, the same framing, the same length.  A cut to the same picture is
not a cut - it is the same shot twice, and the second one is eight
seconds of nothing.

So the two are put back together.  The lines they carry go to the one
shot, and the shot-list repair that follows decides whether that shot
is now too long and has to be cut somewhere else.
"""
import re

_WS = re.compile(r"[\s，,。.、；;：:！!？?…—\-]+")

# "接上：" is a note to the reader, not to the camera.  It says the shot
# continues the one before it, which is true of every shot in a scene
# and means nothing to the model that has to draw it.
_CONNECTOR = re.compile(r"^\s*(接上|承接|继续|延续|同上)[：:，,、\s]*")


def strip_connector(action: str) -> str:
    """Take off the words that say "this shot continues the last one"."""
    return _CONNECTOR.sub("", action or "").strip()


def _same_picture(a, b) -> bool:
    """Are these two shots the same picture?"""
    if a.shot_type != b.shot_type:
        return False
    if (a.angle or "") != (b.angle or ""):
        return False
    if (a.height or "") != (b.height or ""):
        return False
    if (a.camera_move or "") != (b.camera_move or ""):
        return False
    ta = _WS.sub("", strip_connector(a.action))
    tb = _WS.sub("", strip_connector(b.action))
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    # the same picture, said a little differently
    if len(ta) >= 8 and (tb.endswith(ta) or ta.endswith(tb)):
        return True
    return False


def merge_duplicate_shots(sc) -> int:
    """Put the shots that are the same picture back together.

    Returns how many shots were taken out.
    """
    shots = list(getattr(sc, "shots", []) or [])
    if len(shots) < 2:
        return 0
    out = []
    dropped = 0
    for sh in shots:
        if out and _same_picture(out[-1], sh):
            prev = out[-1]
            prev.line_indices = sorted(set(prev.line_indices) | set(sh.line_indices))
            prev.beats = sorted(set(prev.beats) | set(sh.beats))
            if len(sh.characters or []) > len(prev.characters or []):
                prev.characters = list(sh.characters)
            if not prev.purpose and sh.purpose:
                prev.purpose = sh.purpose
            prev.duration = max(float(prev.duration or 0), float(sh.duration or 0))
            dropped += 1
            continue
        out.append(sh)
    if dropped:
        for i, sh in enumerate(out):
            sh.index = i
        sc.shots = out
    return dropped
