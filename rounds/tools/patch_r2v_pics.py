"""The prompt names every picture and says what it is for.

The reference guide is explicit about it: the pictures are numbered and
the prompt says which one carries the identity, which one is the room and
which one is the frame the shot continues from. Without that, the model
spreads the references over the whole description and the person drifts.
"""
from pathlib import Path

# 1) refs.py: the plan carries what each picture is
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\refs.py")
s = p.read_text(encoding="utf-8")
old = '''def picture_plan(ctx: Context, shot, sc) -> list[tuple[str, str]]:
    """The pictures for one shot: (path, what it is).

    Order matters: the character sheets come first (they carry the
    identity), then the location, then the frame the shot continues from.
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    for name in shot.characters or []:
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
        out.append((sheet, f"the three views of {name} "
                           f"(front, profile and three-quarter, left to right)"))

    if sc is not None:
        for loc in ctx.project.locations:
            if loc.name != sc.location:
                continue
            for rel in (loc.ref_images or [])[:1]:
                p = ctx.store.abs(rel)
                if p.exists() and str(p) not in seen:
                    seen.add(str(p))
                    out.append((str(p), f"the room: {loc.name}"))

    if shot.image_path:
        p = ctx.store.abs(shot.image_path)
        if p.exists() and str(p) not in seen:
            out.append((str(p), "the frame this shot continues from"))
    return out'''
new = '''def picture_plan(ctx: Context, shot, sc, *, with_frame: bool = True
                 ) -> list[tuple[str, str, str]]:
    """The pictures for one shot: (path, what it is, kind).

    Order matters: the character sheets come first (they carry the
    identity), then the location, then the frame the shot continues from.
    The frame is listed even before it exists, so the numbering the prompt
    uses is the numbering the video job uses.
    """
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    for name in shot.characters or []:
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
                    "character"))

    if sc is not None:
        for loc in ctx.project.locations:
            if loc.name != sc.location:
                continue
            for rel in (loc.ref_images or [])[:1]:
                p = ctx.store.abs(rel)
                if p.exists() and str(p) not in seen:
                    seen.add(str(p))
                    out.append((str(p), f"the room: {loc.name}", "room"))

    if with_frame and shot.image_path:
        p = ctx.store.abs(shot.image_path)
        if str(p) not in seen:
            out.append((str(p), "the frame this shot continues from", "frame"))
    return out'''
assert old in s, "picture_plan 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("refs.py: 清单带类型")

# 2) promptgen: the prompt names the pictures
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")
old = '''R2V_HEADER = ("subject_definitions:\\n"
              "<Subject 1> is the person in <Picture 1>, with the face, hair, "
              "clothes and the surroundings exactly as shown there.\\n"
              "<Audio 1> is the voice-timbre reference for <Subject 1> (S1), "
              "containing a spoken Mandarin vocal layer.\\n\\n"
              "summary:\\n"
              "[reference generation + audio reference] The target video is a "
              "single shot in the style and place of <Picture 1>, in which "
              "<Subject 1> speaks, using the voice timbre referenced from "
              "<Audio 1>.\\n\\n"
              "retention_analysis:\\n"
              "<Subject 1> (appears in [Shot 1]): fully_preserved - the face, "
              "hair, clothes, the room and the light of <Picture 1> are kept.\\n"
              "<Picture 1> ([Shot 1] composition): fully_preserved - the "
              "framing and the blocking of <Picture 1> are kept.\\n"
              "<Audio 1>: reference - the vocal timbre of <Audio 1> guides how "
              "<Subject 1> speaks, without copying the original signal.\\n\\n"
              "detailed_description:\\n")


def _assemble_r2v_prompt(desc: str, soundscape: str, music: str) -> str:
    """The full-reference format, for the model that speaks."""
    return "\\n".join([
        R2V_HEADER,
        desc.strip(),
        "",
        f"overall_soundscape: {soundscape or 'N/A'}",
        "",
        f"non_diegetic_music: {music or 'N/A'}",
    ])'''
new = '''def _r2v_header(plan: list[tuple[str, str, str]]) -> str:
    """The six sections of the full-reference format, with the pictures named.

    `plan` is the picture list: (path, what it is, kind). The prompt has to
    say which picture carries the identity, which is the room and which is
    the frame the shot continues from - otherwise the model spreads the
    references over the whole description and the person drifts.
    """
    subject = ""
    keep = []
    first_char = ""
    room = ""
    frame = ""
    for i, (_path, role, kind) in enumerate(plan, 1):
        if kind == "character":
            if not first_char:
                first_char = str(i)
                subject += (f"<Picture {i}> is {role}; <Subject 1> is the person "
                            f"in <Picture {i}>, and keeps this face, this hair "
                            f"and this outfit in every single shot.\\n")
            else:
                subject += f"<Picture {i}> is {role}.\\n"
            keep.append(f"<Picture {i}> (the person): fully_preserved - "
                        f"the face, the hair and the clothes are kept exactly.")
        elif kind == "room":
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
            "detailed_description:\\n")


def _assemble_r2v_prompt(desc: str, soundscape: str, music: str,
                         plan: list[tuple[str, str, str]]) -> str:
    """The full-reference format, for the model that speaks."""
    return "\\n".join([
        _r2v_header(plan),
        desc.strip(),
        "",
        f"overall_soundscape: {soundscape or 'N/A'}",
        "",
        f"non_diegetic_music: {music or 'N/A'}",
    ])'''
assert old in s, "R2V_HEADER 锚点没找到"
s = s.replace(old, new, 1)

old = """            if ctx.cfg.comfyui.native_audio:
                # the score has its own music-only clip; the shot clip
                # carries the voice and the room
                shot.video_prompt = _assemble_r2v_prompt(
                    desc, soundscape or "N/A", "N/A")"""
new = """            if ctx.cfg.comfyui.native_audio:
                # the score has its own music-only clip; the shot clip
                # carries the voice and the room
                from .refs import picture_plan
                plan = picture_plan(ctx, shot, sc)
                shot.video_prompt = _assemble_r2v_prompt(
                    desc, soundscape or "N/A", "N/A", plan)"""
assert old in s, "R2V 调用锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py: 提示词逐张点名参考图")
