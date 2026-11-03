"""Repoint the picture numbers in every video prompt, without rewriting them.

Each prompt opens with a header naming its pictures by position, then a
description written by the model. The positions moved: a face and a sheet
of bodies became one picture, so everything after a character shifted down
by one and the last reference now points past the end of the list.

The description never names a picture - checked across all of them - so
the header can be rebuilt from the new list and spliced in, and every
prompt keeps the scene, the camera and the sound it was written with. Only
the sixty-five prompts in the other format are looked at separately,
because those name the frame and nothing else, which did not move.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.providers import Providers      # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import refs as R       # noqa: E402
from dramakit.pipeline import promptgen as PG  # noqa: E402

MARKER = "detailed_description:"
REPO = Path(r"E:\dramakit")
DRY = "--apply" not in sys.argv

out = []
cfg = Config.load(Config.discover())
proj = next(d for d in (REPO / "projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
store = ProjectStore.open(proj)
ctx = Context(cfg, store, Providers(cfg, REPO))

spliced = skipped = unchanged = 0
other_format: list[tuple[str, str]] = []
changed_shots = []

for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            vp = sh.video_prompt or ""
            if not vp:
                skipped += 1
                continue
            plan = R.picture_plan(ctx, sh, sc)
            new_head = PG._r2v_header(plan)

            i = vp.find(MARKER)
            if i < 0:
                # The other format. It names the frame, which is always
                # picture one and so did not move - recorded rather than
                # changed, so it can be checked rather than assumed.
                n = vp.count("<Picture")
                other_format.append((sh.id, f"{n} 处引用"))
                continue

            old_head = vp[:i]
            rest = vp[i + len(MARKER):]
            if old_head == new_head:
                unchanged += 1
                continue

            if old_head.count("<Picture") == new_head.count("<Picture") \
                    and "<Subject 1>" in old_head == "<Subject 1>" in new_head:
                pass   # same shape, different wording - still worth writing

            sh.video_prompt = new_head + MARKER + rest
            spliced += 1
            changed_shots.append(
                (sh.id, old_head.count("<Picture"), new_head.count("<Picture")))

out.append(f"=== {'试运行' if DRY else '已应用'} ===")
out.append(f"  换 header: {spliced}")
out.append(f"  本来就一致: {unchanged}")
out.append(f"  没有 video_prompt: {skipped}")
out.append(f"  另一种格式（只引用 <Picture 1>，未移动）: {len(other_format)}")

if changed_shots:
    out.append("")
    out.append("=== 抽样（旧引用数 -> 新引用数）===")
    for sid, a, b in changed_shots[:6]:
        out.append(f"  {sid}: {a} -> {b}")

if other_format:
    out.append("")
    out.append("=== 另一种格式的引用情况 ===")
    for sid, n in other_format[:6]:
        out.append(f"  {sid}: {n}")

if not DRY:
    ctx.save()
    out.append("")
    out.append("已写入 project.json")
else:
    out.append("")
    out.append("（试运行，未写入；加 --apply 才保存）")

# --- verify after -------------------------------------------------------
if not DRY:
    again = ProjectStore.open(proj).load()
    bad = 0
    maxpic = 0
    for ep in again.episodes:
        for sc in ep.scenes:
            for sh in sc.shots:
                vp = sh.video_prompt or ""
                if not vp:
                    continue
                plan = R.picture_plan(again, sh, sc)
                n = len(plan)
                # the highest picture number the prompt asks for
                import re
                nums = [int(x) for x in re.findall(r"<Picture (\d+)>", vp)]
                if nums:
                    m = max(nums)
                    maxpic = max(maxpic, m)
                    if m > n:
                        bad += 1
                        if bad <= 5:
                            out.append(f"  **越界** {sh.id}: 提示词最大 "
                                       f"<Picture {m}>，实际只有 {n} 张")
    out.append("")
    out.append(f"=== 校验：提示词引用超过实际图片数的镜头: {bad} ===")
    out.append(f"  全项目最大引用编号: {maxpic}")

Path(r"C:\Users\Dev\AppData\Local\Temp\opencode\fixhdr.txt").write_text(
    "\n".join(out), encoding="utf-8") if False else None
Path(r"C:\Users\David\AppData\Local\Temp\opencode\fixhdr.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
