"""The first picture has to be the frame the shot continues from.

The experiments that worked - the ones where H3 spoke a clear Chinese line
- had one picture, the still of the shot, and it was <Picture 1>.  With
four pictures the order was the other way round: the character sheets came
first and the still last, and the model blended them into a scene that was
neither: a different room, a different dress, different faces.

The still IS the composition - the framing, the blocking, the clothes, the
light.  The sheets are the identity, the room picture is the environment.
So the still is the first picture, the sheets follow, and the room last.

The subject definitions have to follow: <Subject 1> is the person in the
first sheet, and <Subject 1> is the one who speaks, and <Audio 1> is that
person's timbre.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")

# --------------------------------------------------------------------------- #
# 1. the plan: the frame first
# --------------------------------------------------------------------------- #
p = ROOT / "dramakit\\pipeline\\refs.py"
s = p.read_text(encoding="utf-8")

old = """    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    for name in shot.characters or []:"""
new = """    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    # The frame comes first: it is the picture the shot continues from, and
    # the model takes the first picture as the one it follows.
    if with_frame:
        rel = shot.image_path or ctx.store.rel(ctx.store.image_path(shot.id))
        p = ctx.store.abs(rel)
        if str(p) not in seen:
            seen.add(str(p))
            out.append((str(p), "the frame this shot continues from", "frame"))

    for name in shot.characters or []:"""
assert old in s, "refs 清单开头锚点没找到"
s = s.replace(old, new, 1)

old = """    if with_frame:
        # The slot is reserved even before the still is on disk: the prompt
        # names its references by number, and the number has to be the same
        # in the prompt and in the job that uploads them.
        rel = shot.image_path or ctx.store.rel(ctx.store.image_path(shot.id))
        p = ctx.store.abs(rel)
        if str(p) not in seen:
            seen.add(str(p))
            out.append((str(p), "the frame this shot continues from", "frame"))
    return out"""
new = """    return out"""
assert old in s, "refs 清单结尾锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("refs.py: 首帧排到清单第一位")

# --------------------------------------------------------------------------- #
# 2. the header: the subject is the first sheet, the anchor is the frame
# --------------------------------------------------------------------------- #
p = ROOT / "dramakit\\pipeline\\promptgen.py"
s = p.read_text(encoding="utf-8")
old = """        elif kind == "room":
            room = str(i)
            keep.append(f"<Picture {i}> (the room): fully_preserved - the "
                        f"furniture, the light and the layout are kept.")
        else:
            frame = str(i)
            keep.append(f"<Picture {i}> (the frame this shot continues from): "
                        f"fully_preserved - the framing and the blocking are kept.")
    if not subject:
        subject = "<Subject 1> is the person in <Picture 1>.\\n"
    anchor = frame or room or first_char or "1"
    return ("subject_definitions:\\n"
            f"{subject}"
            "<Audio 1> is the voice-timbre reference for <Subject 1> (S1), "
            "containing a spoken Mandarin vocal layer.\\n\\n"
            "summary:\\n"
            f"[reference generation + audio reference] The target video is a "
            f"single shot in the style and place of <Picture {anchor}>, in which "
            "<Subject 1> speaks, using the voice timbre referenced from "
            "<Audio 1>. The person is the one in the reference sheet, not "
            "somebody who looks like them.\\n\\n"
            "retention_analysis:\\n"
            "<Subject 1> (appears in [Shot 1]): fully_preserved - the same "
            "person as in the reference sheet.\\n"
            + "\\n".join(keep) + "\\n"
            "<Audio 1>: reference - the vocal timbre of <Audio 1> guides how "
            "<Subject 1> speaks, without copying the original signal.\\n\\n"
            "detailed_description:\\n")"""
new = """        elif kind == "room":
            room = str(i)
            keep.append(f"<Picture {i}> (the room): fully_preserved - the "
                        f"furniture, the light and the layout are kept.")
        elif kind == "frame":
            frame = str(i)
            keep.append(f"<Picture {i}> (the frame this shot continues from): "
                        f"fully_preserved - the framing, the blocking, the "
                        f"clothes, the faces and the light are kept.")
        else:
            keep.append(f"<Picture {i}> (the prop): fully_preserved - the "
                        f"shape, the colour and the material are kept.")
    if not subject:
        subject = "<Subject 1> is the person in <Picture 1>.\\n"
    anchor = frame or room or first_char or "1"
    if frame:
        # the frame is the picture the shot goes on from: the video has to
        # be that picture, moving
        how = (f"[reference generation + audio reference] The target video is "
               f"a single shot that continues <Picture {anchor}>: the same "
               f"framing, the same people, the same clothes and the same "
               f"light, in which <Subject 1> speaks, using the voice timbre "
               f"referenced from <Audio 1>. The person is the one in the "
               f"reference sheet, not somebody who looks like them.")
    else:
        how = (f"[reference generation + audio reference] The target video is a "
               f"single shot in the style and place of <Picture {anchor}>, in "
               f"which <Subject 1> speaks, using the voice timbre referenced "
               f"from <Audio 1>. The person is the one in the reference sheet, "
               f"not somebody who looks like them.")
    return ("subject_definitions:\\n"
            f"{subject}"
            "<Audio 1> is the voice-timbre reference for <Subject 1> (S1), "
            "containing a spoken Mandarin vocal layer.\\n\\n"
            "summary:\\n"
            f"{how}\\n\\n"
            "retention_analysis:\\n"
            "<Subject 1> (appears in [Shot 1]): fully_preserved - the same "
            "person as in the reference sheet.\\n"
            + "\\n".join(keep) + "\\n"
            "<Audio 1>: reference - the vocal timbre of <Audio 1> guides how "
            "<Subject 1> speaks, without copying the original signal.\\n\\n"
            "detailed_description:\\n")"""
assert old in s, "promptgen 头部锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py: 头部改成首帧当主图")

# --------------------------------------------------------------------------- #
# 3. the prompts that are already written get their header again
# --------------------------------------------------------------------------- #
import sys  # noqa: E402

sys.path.insert(0, str(ROOT))
from dramakit.config import Config  # noqa: E402
from dramakit.pipeline.base import Context  # noqa: E402
from dramakit.pipeline.promptgen import _r2v_header  # noqa: E402
from dramakit.pipeline.refs import picture_plan  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
eps = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [1]
cfg = Config.load(str(ROOT / "config\\default.yaml"))
store = ProjectStore(ROOT / "projects" / name)
ctx = Context(cfg, store)

fixed = 0
for ep in ctx.project.episodes:
    if ep.index not in eps:
        continue
    for sc in ep.scenes:
        for shot in sc.shots:
            vp = shot.video_prompt or ""
            if not vp or "detailed_description:" not in vp:
                continue
            plan = picture_plan(ctx, shot, sc)
            new = _r2v_header(plan) + vp[vp.index("detailed_description:"):]
            if new != vp:
                shot.video_prompt = new
                fixed += 1
ctx.save()
print(f"{name}: 重建了 {fixed} 条提示词的头部（首帧当主图）")
