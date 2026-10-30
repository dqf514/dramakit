"""Who is in the frame, and who speaks first.

The picture of a shot is drawn from its action, and the video is given
reference sheets of the people in the shot's list.  Two things were wrong.

The list did not always agree with the action: a shot whose action names
苏晚 and 林薇薇 still had 苏父 and 苏母 in the list, so the video was
handed faces that are not in the picture and was missing the face that is.

And the first name in the list was not always the one who speaks.  The
prompt says <Subject 1> is the person in <Picture 1> and that <Subject 1>
is the one who speaks, and <Audio 1> is the timbre reference for that same
person - so the speaker has to be first in the list, or the prompt says the
wrong person is talking.

So: the people who speak in the shot come first, and the list is the people
the action names.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")

REPAIR = '''
def _repair_characters(ctx, sc) -> int:
    """Make the shot's list agree with its action, speaker first.

    The picture is drawn from the action and the video is given reference
    sheets of the people in the list, so the two have to agree.  The person
    who speaks the shot goes first: <Subject 1> is the person in
    <Picture 1>, <Subject 1> is the one who speaks, and <Audio 1> is the
    timbre reference for that same person.
    """
    names = [c.name for c in ctx.project.characters if c.name]
    spoken = [l for l in sc.lines if not is_narration(l)]
    changed = 0
    for shot in sc.shots:
        action = shot.action or ""
        # the people the action puts in the frame, in the order it puts
        # them there
        named = []
        for n in names:
            at = action.find(n)
            if at >= 0:
                named.append((at, n))
        named = [n for _at, n in sorted(named)]
        if not named:
            continue
        # the one who speaks the shot comes first
        first = ""
        for idx in (shot.line_indices or []):
            if 1 <= idx <= len(spoken):
                spk = spoken[idx - 1].speaker
                if spk in named:
                    first = spk
                    break
        keep = [n for n in (shot.characters or []) if n in named]
        merged = list(dict.fromkeys(([first] if first else []) + named + keep))
        if merged != (shot.characters or []):
            shot.characters = merged
            changed += 1
    return changed

'''

# --------------------------------------------------------------------------- #
# the storyboard stage uses it from now on
# --------------------------------------------------------------------------- #
p = ROOT / "dramakit\\pipeline\\storyboard.py"
s = p.read_text(encoding="utf-8")
old = """            sc.shots = shots or _fallback_shots(sc, dmin, dmax)
            _repair_line_casts(sc)"""
new = """            sc.shots = shots or _fallback_shots(sc, dmin, dmax)
            _repair_line_casts(sc)
            _repair_characters(ctx, sc)"""
assert old in s, "storyboard 的修复调用锚点没找到"
s = s.replace(old, new, 1)

old2 = """def _repair_line_casts(sc) -> int:"""
new2 = REPAIR + """
def _repair_line_casts(sc) -> int:"""
assert old2 in s, "storyboard 的插入锚点没找到"
s = s.replace(old2, new2, 1)
p.write_text(s, encoding="utf-8")
print("storyboard.py: 加了角色表修复")

# --------------------------------------------------------------------------- #
# and the shots that are already written get it now
# --------------------------------------------------------------------------- #
import sys  # noqa: E402

sys.path.insert(0, str(ROOT))
from dramakit.config import Config  # noqa: E402
from dramakit.pipeline.base import Context  # noqa: E402
from dramakit.pipeline.storyboard import _repair_characters  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
cfg = Config.load(str(ROOT / "config\\default.yaml"))
store = ProjectStore(ROOT / "projects" / name)
ctx = Context(cfg, store)

redo: list[str] = []
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        before = [list(sh.characters or []) for sh in sc.shots]
        _repair_characters(ctx, sc)
        for sh, old_chars in zip(sc.shots, before):
            if list(sh.characters or []) != old_chars:
                redo.append(sh.id)
ctx.save()
print(f"{name}: {len(redo)} 个镜头的角色表改了")
print("  " + "、".join(redo))
