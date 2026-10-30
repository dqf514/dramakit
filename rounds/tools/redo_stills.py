"""The stills of the shots whose people changed have to be drawn again.

A still is made with the character sheets as its reference, so when the
list of people changes, the still that was drawn with the old sheets is a
picture of somebody else.  Those stills are removed, and the prompts are
given their headers again - <Picture 1> is now somebody else.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _r2v_header
from dramakit.pipeline.refs import picture_plan
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
eps = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [1]

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
ctx = Context(cfg, store)

removed = 0
heads = 0
for ep in ctx.project.episodes:
    if ep.index not in eps:
        continue
    for sc in ep.scenes:
        for shot in sc.shots:
            # the still was drawn with the sheets of the people this shot
            # had before; the action says who is in the frame now
            names = {c.name for c in ctx.project.characters}
            named = {n for n in names if n in (shot.action or "")}
            if named and named != set(shot.characters or []):
                continue
            img = ctx.store.image_path(shot.id)
            if img.exists():
                img.unlink()
                shot.image_path = ""
                removed += 1
            vp = shot.video_prompt or ""
            if vp and "detailed_description:" in vp:
                plan = picture_plan(ctx, shot, sc)
                shot.video_prompt = _r2v_header(plan) + vp[vp.index("detailed_description:"):]
                heads += 1
ctx.save()
print(f"删掉 {removed} 张要重画的首帧，重建 {heads} 条提示词的头部")
