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

from ..models import ShotType

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


# The angles a camera can be at.  The three-quarter one is the one every
# model reaches for first, and a drama shot entirely in the three-quarter
# is the most amateur-looking picture there is.
_SIDE_ANGLES = ("斜侧", "正侧", "后斜侧", "背面")
# the angle the model leans on
_DEFAULT_ANGLE = "斜侧"


def _angle_fits(shot, angle: str) -> bool:
    """Does this angle say what the action says?

    The action sometimes says which way the person is turned, and an
    angle that contradicts it is worse than a repeated one.
    """
    action = shot.action or ""
    if angle in ("斜侧", "正侧"):
        if any(w in action for w in ("背影", "背对")):
            return False
        return True
    if angle == "背面":
        return any(w in action for w in ("背影", "背对", "转身"))
    return True


def _other_angle(shot, current: str, avoid=()) -> str:
    """An angle this shot can take, and that says something different."""
    action = shot.action or ""
    if any(w in action for w in ("侧脸", "侧面", "侧身")):
        choices = ("正侧", "斜侧", "后斜侧")
    elif any(w in action for w in ("背影", "背对")):
        choices = ("背面", "后斜侧", "斜侧")
    else:
        choices = _SIDE_ANGLES
    for c in choices:
        if c == current or c in avoid:
            continue
        if not _angle_fits(shot, c):
            continue
        return c
    return ""


def _other_size(shot, current: str) -> str:
    """A size this shot can take, one step away from the one it has.

    A detail is a detail - it does not become a wide shot - and a shot
    that is about the room can afford to come in closer.
    """
    action = shot.action or ""
    detail = any(w in action for w in ("特写", "眼睛", "睫毛", "指尖", "嘴角",
                                       "眉", "掌心", "指节"))
    if detail:
        choices = ("特写", "近景")
    else:
        choices = ("近景", "中景", "全景")
    for c in choices:
        if c != current:
            return c
    return ""


def enforce_variety(sc) -> int:
    """A shot list that is one framing repeated is not a shot list.

    The model writes good shots and then writes the same one again: the
    same size, the same three-quarter angle, the same person in it.
    The cut is what the audience sees, so the framings have to differ -
    and the angle the model leans on is the one that has to be turned.

    Returns how many shots were changed.
    """
    shots = list(getattr(sc, "shots", []) or [])
    if len(shots) < 2:
        return 0
    changed = 0
    # 1. two shots in a row with the same size and the same angle
    for i in range(1, len(shots)):
        a, b = shots[i - 1], shots[i]
        if (a.shot_type.value, a.angle) != (b.shot_type.value, b.angle):
            continue
        new = _other_angle(b, b.angle or a.angle)
        if new:
            b.angle = new
            changed += 1
    # 2. two shots in a row with the same size: the size has to move,
    #    and the angle with it
    for i in range(1, len(shots)):
        a, b = shots[i - 1], shots[i]
        if a.shot_type.value != b.shot_type.value:
            continue
        new = _other_size(b, b.shot_type.value)
        if new:
            try:
                b.shot_type = ShotType(new)
            except ValueError:
                continue
            changed += 1
    # 3. the three-quarter angle, everywhere
    side = [s for s in shots if (s.angle or "") == _DEFAULT_ANGLE]
    limit = max(1, len(shots) // 2)
    if len(side) > limit:
        for s in side[limit:]:
            new = _other_angle(s, _DEFAULT_ANGLE, avoid=(_DEFAULT_ANGLE,))
            if new:
                s.angle = new
                changed += 1
    # 4. a camera that never moves
    still = [s for s in shots if (s.camera_move or "") == "固定"]
    if len(still) > max(1, len(shots) // 2):
        moves = ("推", "拉", "摇", "移", "跟")
        for s in still[max(1, len(shots) // 2):]:
            if s.action and "固定" in s.action:
                continue
            s.camera_move = moves[(changed + len(s.id)) % len(moves)]
            changed += 1
    return changed
