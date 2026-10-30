"""The frame has to be in the picture list from the start.

The prompt names its references by number - <Picture 1> is the first sheet,
<Picture 2> the second - and the job uploads them in the same order.  But
when the prompt is written the still of the shot does not exist yet, so the
frame was left out of the list: the prompt said "Picture 3 is the room" and
the job uploaded the room third and the frame fourth, and nobody ever said
in the prompt what the fourth picture was.

The slot is reserved now, whether or not the picture is on disk yet.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")

# --------------------------------------------------------------------------- #
# 1. the slot is reserved
# --------------------------------------------------------------------------- #
p = ROOT / "dramakit\\pipeline\\refs.py"
s = p.read_text(encoding="utf-8")
old = """    if with_frame and shot.image_path:
        p = ctx.store.abs(shot.image_path)
        if str(p) not in seen:
            out.append((str(p), "the frame this shot continues from", "frame"))
    return out"""
new = """    if with_frame:
        # The slot is reserved even before the still is on disk: the prompt
        # names its references by number, and the number has to be the same
        # in the prompt and in the job that uploads them.
        rel = shot.image_path or ctx.store.rel(ctx.store.image_path(shot.id))
        p = ctx.store.abs(rel)
        if str(p) not in seen:
            seen.add(str(p))
            out.append((str(p), "the frame this shot continues from", "frame"))
    return out"""
assert old in s, "refs.py 的首帧槽位锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("refs.py: 首帧槽位预留了")

# --------------------------------------------------------------------------- #
# 2. the prompts that are already written get their header rebuilt
# --------------------------------------------------------------------------- #
import sys  # noqa: E402

sys.path.insert(0, str(ROOT))
from dramakit.config import Config  # noqa: E402
from dramakit.pipeline.base import Context  # noqa: E402
from dramakit.pipeline.promptgen import _r2v_header  # noqa: E402
from dramakit.pipeline.refs import picture_plan  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
cfg = Config.load(str(ROOT / "config\\default.yaml"))
store = ProjectStore(ROOT / "projects" / name)
ctx = Context(cfg, store)

fixed = 0
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for shot in sc.shots:
            vp = shot.video_prompt or ""
            if not vp or "detailed_description:" not in vp:
                continue
            plan = picture_plan(ctx, shot, sc)
            head = _r2v_header(plan)
            body = vp[vp.index("detailed_description:"):]
            new = head + body
            if new != vp:
                shot.video_prompt = new
                fixed += 1
ctx.save()
print(f"{name}: 重建了 {fixed} 条提示词的头部")
