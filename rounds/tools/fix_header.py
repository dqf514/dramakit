"""Rebuild the header of the prompts, without the marks that piled up.

The header is written by the code - it names the pictures, the subject and
the voice reference - and the body is written by the model.  Rebuilding
the header after the fact put the mark that starts the body in twice, and
rebuilding it again put it in four times.  The model reads those marks, so
they are cleared now: the header is rebuilt from the picture list and the
body keeps one.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _r2v_header
from dramakit.pipeline.refs import picture_plan
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1
            else r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
eps = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(root)
ctx = Context(cfg, store)

MARK = "detailed_description:"
fixed = 0
for ep in ctx.project.episodes:
    if eps and ep.index not in eps:
        continue
    for sc in ep.scenes:
        for shot in sc.shots:
            vp = shot.video_prompt or ""
            if not vp or MARK not in vp:
                continue
            body = vp[vp.rfind(MARK) + len(MARK):]
            plan = picture_plan(ctx, shot, sc)
            new = _r2v_header(plan) + body
            if new != vp:
                shot.video_prompt = new
                fixed += 1
ctx.save()
print(f"{root}: 重建了 {fixed} 条提示词的头部")
