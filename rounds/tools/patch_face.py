"""A character is only as consistent as the picture the model is given.

The reference pictures were full body: the face was a small part of a tall
photograph, and the model had to guess the face from it.  So the reference
carries a shot of the face filling the frame - drawn from the full body
picture, so it is the same person - and the video is given that one.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")


def patch(path: str, pairs: list[tuple[str, str]]) -> None:
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s and old not in s:
            print(f"  {path}: 已经打过补丁了")
            continue
        assert old in s, f"{path}: 锚点没找到\n{old[:200]}"
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"  {path}: 改好了")


# --------------------------------------------------------------------------- #
# 1. the face view
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/character.py", [
    ("""VIEW_TEXT = {
    "front": "front view, facing the camera, neutral standing pose",""",
     """VIEW_TEXT = {
    "front": "front view, facing the camera, neutral standing pose",
    "face": "tight close-up of the face, the face filling the frame","""),
    ("""FLUX3_VIEW = {
    "front": "seen from the front, facing the camera, standing at ease",""",
     """FLUX3_VIEW = {
    "front": "seen from the front, facing the camera, standing at ease",
    "face": ("seen in a tight head-and-shoulders close-up, the face filling "
             "the frame and looking straight into the camera, every feature "
             "sharp and unobstructed"),"""),
    # the prompt for the face view: not the whole body
    ("""    if ctx.cfg.comfyui.prompt_format == "flux3":
        return (
            f"Full-color studio photograph, full-body portrait of {c.anchor()}, \"""",
     """    if view == "face":
        # the face, filling the frame: this is the picture that keeps the
        # face the same from one shot to the next
        if derived:
            return (
                f"Full-color studio photograph, the same face as in the "
                f"reference picture - identical face, identical hair, "
                f"identical clothes - now a tight head-and-shoulders close-up. "
                f"The face fills the frame, looking straight into the camera, "
                f"every feature sharp and unobstructed, photographed against a "
                f"plain light gray seamless backdrop, soft even light from the "
                f"front, natural skin texture, no props, no text, no "
                f"watermark, {style}."
            )
        return (
            f"Full-color studio photograph, a tight head-and-shoulders "
            f"close-up portrait of {c.anchor()}, "
            f"{FLUX3_VIEW['face']}. The face fills the frame, every feature "
            f"sharp and unobstructed, photographed against a plain light gray "
            f"seamless backdrop, soft even light from the front, natural skin "
            f"texture, a neutral expression, no props, no text, no watermark, "
            f"{style}."
        )
    if ctx.cfg.comfyui.prompt_format == "flux3":
        return (
            f"Full-color studio photograph, full-body portrait of {c.anchor()}, \""""),
])

# --------------------------------------------------------------------------- #
# 2. the picture list: the face, not the sheet of the body
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/refs.py", [
    ("""    for name in shot.characters or []:
        c = ctx.project.character(name)
        if c is None:
            continue
        refs = []
        for rel in c.refs():
            p = ctx.store.abs(rel)
            if p.exists():
                refs.append(p)
        if not refs:
            continue
        sheet = _sheet(ctx, name, refs)
        if sheet in seen:
            continue
        seen.add(sheet)
        out.append((sheet,
                    f"the views of {name} "
                    f"(front, profile, three-quarter and back, left to right)",
                    "character"))""",
     """    for name in shot.characters or []:
        c = ctx.project.character(name)
        if c is None:
            continue
        refs = []
        for rel in c.refs():
            p = ctx.store.abs(rel)
            if p.exists():
                refs.append(p)
        if not refs:
            continue
        # The face is what has to stay the same, and a face in a full-body
        # photograph is a small face.  So the reference is the picture of the
        # face filling the frame, and the sheet of the body is only used when
        # there is no such picture.
        face = _face_picture(ctx, name, refs)
        if face is None:
            face = _sheet(ctx, name, refs)
            role = (f"the views of {name} "
                    f"(front, profile, three-quarter and back, left to right)")
        else:
            role = f"the face of {name}, filling the frame, looking at the camera"
        if face in seen:
            continue
        seen.add(face)
        out.append((face, role, "character"))"""),
    # the helper
    ("""def picture_plan(ctx: Context, shot, sc, *, with_frame: bool = True""",
     '''def _face_picture(ctx: Context, name: str, refs: list[Path]) -> str | None:
    """The picture of the face filling the frame, if there is one."""
    for rel in ctx.project.character(name).refs():
        if "face" not in rel.lower():
            continue
        p = ctx.store.abs(rel)
        if p.exists():
            return str(p)
    return None


def picture_plan(ctx: Context, shot, sc, *, with_frame: bool = True'''),
])
