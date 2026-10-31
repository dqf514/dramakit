"""Put the cut markers into the prompts that are already written.

The prompt generator does this when it writes a prompt.  This does it for
the prompts that are already there: the cuts come from the shots the
director wrote inside the segment, and a segment the director left with
one shot is cut in the middle.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _cut_marks, _r2v_header
from dramakit.pipeline.refs import picture_plan
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1
            else r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
eps = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(root)
ctx = Context(cfg, store)

fixed = 0
for ep in ctx.project.episodes:
    if eps and ep.index not in eps:
        continue
    for sc in ep.scenes:
        for shot in sc.shots:
            vp = shot.video_prompt or ""
            if not vp or "[Shot 2]" in vp:
                continue
            marks = _cut_marks(shot)
            if not marks:
                continue
            body = vp[vp.rfind("detailed_description:") + len("detailed_description:"):]
            shot.video_prompt = (_r2v_header(picture_plan(ctx, shot, sc))
                                 + body.rstrip() + "\n" + "\n".join(marks))
            fixed += 1
ctx.save()
print(f"{root}: 给 {fixed} 个片段补上了切点")
