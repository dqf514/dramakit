"""Whether the headers were rewritten, and whether any prompt now asks for a picture that is not there.

The fix wrote before it crashed in the check after, so the record may be
good while the report says nothing. The real test is the one that matters:
for every prompt, the highest picture number it names against the number
of pictures the plan actually produces.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.providers import Providers      # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import refs as R       # noqa: E402

REPO = Path(r"E:\dramakit")
out = []
cfg = Config.load(Config.discover())
proj = next(d for d in (REPO / "projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
ctx = Context(cfg, ProjectStore.open(proj), Providers(cfg, REPO))

MARKER = "detailed_description:"
total = spliced_now = with_marker = 0
bad = []
max_ref = 0
max_plan = 0
kind_counts: dict[str, int] = {}

for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            vp = sh.video_prompt or ""
            if not vp:
                continue
            total += 1
            plan = R.picture_plan(ctx, sh, sc)
            n = len(plan)
            max_plan = max(max_plan, n)
            for _p, _r, kind in plan:
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
            if MARKER in vp:
                with_marker += 1
                head = vp[:vp.find(MARKER)]
                new_head = PG_HEAD = None
            nums = [int(x) for x in re.findall(r"<Picture (\d+)>", vp)]
            if nums:
                m = max(nums)
                max_ref = max(max_ref, m)
                if m > n:
                    bad.append((sh.id, m, n, vp[:vp.find(MARKER)][:0]))

out.append(f"=== {total} 条 video_prompt ===")
out.append(f"  含 r2v 标记: {with_marker}")
out.append(f"  提示词最大引用编号: {max_ref}")
out.append(f"  计划最大图片数: {max_plan}")
out.append(f"  **引用越界: {len(bad)} 条**")
for sid, m, n, _ in bad[:8]:
    out.append(f"    {sid}: 引用 <Picture {m}>，实际 {n} 张")

# --- is the new wording in place? --------------------------------------
out.append("")
out.append("=== header 是否已是四视图措辞 ===")
old_style = new_style = 0
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            vp = sh.video_prompt or ""
            if not vp or MARKER not in vp:
                continue
            head = vp[:vp.find(MARKER)]
            if "is the face of" in head and "filling the frame" in head:
                old_style += 1
            if "character sheet of" in head:
                new_style += 1
out.append(f"  旧措辞（face, filling the frame）: {old_style}")
out.append(f"  新措辞（character sheet of）    : {new_style}")

# --- sample ------------------------------------------------------------
out.append("")
out.append("=== 样本 ===")
shown = 0
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            vp = sh.video_prompt or ""
            if MARKER not in vp or shown >= 2:
                continue
            plan = R.picture_plan(ctx, sh, sc)
            out.append(f"--- {sh.id}（{len(plan)} 图）---")
            for i, (p, role, kind) in enumerate(plan, 1):
                out.append(f"  <Picture {i}> [{kind}] {Path(p).name}")
            head = vp[:vp.find(MARKER)]
            for line in head.split("\n")[:5]:
                out.append(f"  | {line[:170]}")
            out.append("")
            shown += 1

out.append("=== 各类参考图总数 ===")
for k, v in sorted(kind_counts.items(), key=lambda x: -x[1]):
    out.append(f"  {k:10} {v}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\verify_hdr.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
