"""Make the stills in the shape they are going to be shown in."""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\visual.py")
s = p.read_text(encoding="utf-8")

old = """    c = ctx.cfg.comfyui
    img_out = ctx.store.image_path(shot.id)
    end_out = ctx.store.end_image_path(shot.id)
    seed = _seed_for(ctx, shot)
    meta: dict = {"seed": seed, "mode": c.mode}"""
new = """    c = ctx.cfg.comfyui
    iw, ih = _image_size(ctx)
    img_out = ctx.store.image_path(shot.id)
    end_out = ctx.store.end_image_path(shot.id)
    seed = _seed_for(ctx, shot)
    meta: dict = {"seed": seed, "mode": c.mode}"""
assert old in s, "gen_image 锚点没找到"
s = s.replace(old, new, 1)

old = """                width=c.width, height=c.height, seed=seed, steps=c.steps, cfg=c.cfg,
                out_path=str(img_out), extra=_extra(ctx), ref_images=refs)"""
new = """                width=iw, height=ih, seed=seed, steps=c.steps, cfg=c.cfg,
                out_path=str(img_out), extra=_extra(ctx), ref_images=refs)"""
assert old in s, "generate_image 锚点没找到"
s = s.replace(old, new, 1)

old = """            ff.fit_reference(path, dst, c.width, c.height)"""
new = """            ff.fit_reference(path, dst, iw, ih)"""
assert old in s, "fit_reference 锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("visual.py 已打补丁")
