"""One person, not four.

The views of a character were four separate pictures, each one its own
generation - so the "same" character had a different face in every panel,
and the model picked whichever it liked. The teacher's method is the
right one: one full-body picture is the master, and the other views are
made from it by editing the picture, so there is only ever one person.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\character.py")
s = p.read_text(encoding="utf-8")

# 1) the prompt of a derived view says it is the same person
old = '''def _ref_prompt(ctx: Context, c: Character, view: str) -> str:
    ad = ctx.project.art_direction
    style = ad.style_prompt_prefix or ad.style or "cinematic realistic"
    if ctx.cfg.comfyui.prompt_format == "flux3":
        return (
            f"Full-color studio photograph, full-body portrait of {c.anchor()}, "
            f"{FLUX3_VIEW.get(view, FLUX3_VIEW['front'])}. The whole body is "
            f"visible from head to feet, centered in the frame with a little "
            f"space around it, photographed against a plain light gray seamless "
            f"backdrop, soft even light from the front, natural skin texture and "
            f"fabric detail, a neutral expression, no props, no text, no "
            f"watermark, {style}."
        )'''
new = '''def _ref_prompt(ctx: Context, c: Character, view: str,
                derived: bool = False) -> str:
    ad = ctx.project.art_direction
    style = ad.style_prompt_prefix or ad.style or "cinematic realistic"
    if derived:
        # the same person as in the reference picture, only turned
        return (
            f"Full-color studio photograph, the same person as in the "
            f"reference picture - identical face, identical hair, identical "
            f"clothes - now {FLUX3_VIEW.get(view, FLUX3_VIEW['front'])}. "
            f"The whole body is visible from head to feet, centered in the "
            f"frame with a little space around it, photographed against a plain "
            f"light gray seamless backdrop, soft even light from the front, "
            f"natural skin texture and fabric detail, a neutral expression, "
            f"no props, no text, no watermark, {style}."
        )
    if ctx.cfg.comfyui.prompt_format == "flux3":
        return (
            f"Full-color studio photograph, full-body portrait of {c.anchor()}, "
            f"{FLUX3_VIEW.get(view, FLUX3_VIEW['front'])}. The whole body is "
            f"visible from head to feet, centered in the frame with a little "
            f"space around it, photographed against a plain light gray seamless "
            f"backdrop, soft even light from the front, natural skin texture and "
            f"fabric detail, a neutral expression, no props, no text, no "
            f"watermark, {style}."
        )'''
assert old in s, "_ref_prompt 锚点没找到"
s = s.replace(old, new, 1)

# 2) the loop: the first view is the master, the rest come from it
old = """    made = 0
    for view in views:
        out = ctx.store.character_ref_path(c.name, view, "png")
        try:
            vis.generate_image(
                prompt=_ref_prompt(ctx, c, view), negative=negative,
                width=cfg.ref_width, height=cfg.ref_height,
                seed=_seed(c.name, view), steps=ccfg.steps, cfg=ccfg.cfg,
                out_path=str(out),
                extra={"sampler": ccfg.sampler, "scheduler": ccfg.scheduler,
                       "checkpoint": ccfg.checkpoint})
            rel = ctx.store.rel(out)
            if rel not in c.ref_images:
                c.ref_images.append(rel)
            if not c.ref_sheet:
                c.ref_sheet = rel
            made += 1"""
new = """    made = 0
    master = ""
    for view in views:
        out = ctx.store.character_ref_path(c.name, view, "png")
        try:
            # the first view is the master; the other views are made from
            # it, so the four panels are one person
            refs = [master] if master else []
            vis.generate_image(
                prompt=_ref_prompt(ctx, c, view, derived=bool(master)),
                negative=negative,
                width=cfg.ref_width, height=cfg.ref_height,
                seed=_seed(c.name, view), steps=ccfg.steps, cfg=ccfg.cfg,
                out_path=str(out),
                extra={"sampler": ccfg.sampler, "scheduler": ccfg.scheduler,
                       "checkpoint": ccfg.checkpoint},
                ref_images=refs)
            rel = ctx.store.rel(out)
            if rel not in c.ref_images:
                c.ref_images.append(rel)
            if not c.ref_sheet:
                c.ref_sheet = rel
            if not master:
                master = str(out)
            made += 1"""
assert old in s, "循环锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("character.py: 一张母图派生其余视图")
