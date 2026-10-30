"""The prop library.

The tutorial puts it plainly: an asset library is the characters, the
locations and the props. A ring that is on the table in one shot, in her
hand in the next and in a box in the third is not a prop, it is a
continuity mistake waiting to happen. So the props are assets too: they
get a picture, and the picture travels with every shot that shows them.
"""
from pathlib import Path

# 1) the model
p = Path(r"E:\\dramakit\\dramakit\\models.py")
s = p.read_text(encoding="utf-8")
old = """class ArtDirection(BaseModel):"""
new = '''class Prop(BaseModel):
    """One recurring object the story keeps returning to."""
    name: str
    description: str = ""
    visual_prompt: str = ""                 # english, for the picture
    ref_images: list[str] = Field(default_factory=list)
    ref_sheet: str = ""


class ArtDirection(BaseModel):'''
assert old in s, "Prop 模型锚点没找到"
s = s.replace(old, new, 1)

old = """    locations: list[Location] = Field(default_factory=list)"""
new = """    locations: list[Location] = Field(default_factory=list)
    props: list[Prop] = Field(default_factory=list)"""
assert old in s, "Project props 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("models.py: Prop")

# 2) the analyze stage reads the props
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\analyze.py")
s = p.read_text(encoding="utf-8")
old = """from ..models import ArtDirection, Character, Location"""
new = """from ..models import ArtDirection, Character, Location, Prop"""
assert old in s, "analyze import 锚点没找到"
s = s.replace(old, new, 1)

old = """    ctx.project.locations = locs"""
new = """    ctx.project.locations = locs
    # the props: the objects the story keeps coming back to
    ctx.project.props = [
        Prop(name=str(p["name"]).strip(),
             description=p.get("description", ""),
             visual_prompt=p.get("visual_prompt", ""))
        for p in (data.get("props") or []) if p.get("name")]"""
assert old in s, "analyze props 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("analyze.py: 道具读进来了")

# 3) the picture plan: the props the shot shows come along
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\refs.py")
s = p.read_text(encoding="utf-8")
old = """    if with_frame and shot.image_path:"""
new = """    # the props this shot shows: they are assets too
    for prop in (getattr(ctx.project, "props", None) or []):
        if not prop.ref_images:
            continue
        if prop.name not in (shot.action or "") and \\
                prop.name not in " ".join(shot.characters or []):
            continue
        for rel in prop.ref_images[:1]:
            pp = ctx.store.abs(rel)
            if pp.exists() and str(pp) not in seen:
                seen.add(str(pp))
                out.append((str(pp), f"the prop: {prop.name}", "prop"))

    if with_frame and shot.image_path:"""
assert old in s, "refs props 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("refs.py: 道具进参考图清单")
