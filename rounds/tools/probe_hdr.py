"""Whether the picture numbers live only in the header, or in the description too.

The video prompt is assembled as a header built from the picture list,
then a description written by the model. If the numbers appear only in the
header, the header can be rebuilt from the new list and spliced in, and
the two hundred prompts keep the scenes they were written with. If the
description names pictures as well, splicing leaves half of them pointing
at the wrong image and the prompts have to be written again.

So each prompt is split at the marker the header always ends with, and the
two halves are searched separately.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))

MARKER = "detailed_description:"
out = []
total = 0
with_marker = 0
header_hits = 0
body_hits = 0
body_samples = []
no_marker = []

for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            vp = sh.get("video_prompt") or ""
            if not vp:
                continue
            total += 1
            i = vp.find(MARKER)
            if i < 0:
                no_marker.append(sh.get("id"))
                continue
            with_marker += 1
            head, body = vp[:i], vp[i + len(MARKER):]
            h = head.count("<Picture")
            b = body.count("<Picture")
            header_hits += h
            body_hits += b
            if b and len(body_samples) < 3:
                # show where in the body
                j = body.find("<Picture")
                body_samples.append((sh.get("id"), body[max(0, j - 120):j + 160]))

out.append(f"=== {total} 条 video_prompt ===")
out.append(f"  含 '{MARKER}' 标记: {with_marker}")
out.append(f"  不含标记: {len(no_marker)}  {no_marker[:6]}")
out.append(f"  header 里的 <Picture 引用: {header_hits}")
out.append(f"  description 里的 <Picture 引用: {body_hits}")

out.append("")
if body_hits == 0 and with_marker == total:
    out.append("**可以只换 header**：图片引用全部在 header 内，")
    out.append("  description 不含 <Picture>，零 LLM 调用即可改完。")
else:
    out.append("**需要重写**：description 里也有图片引用" if body_hits
               else "**部分提示词没有标记**，需要单独处理")
    for sid, s in body_samples:
        out.append(f"  [{sid}] …{s}…")

# --- what the header looks like, old vs new ----------------------------
from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.providers import Providers      # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import refs as R       # noqa: E402
from dramakit.pipeline import promptgen as PG  # noqa: E402

REPO = Path(r"E:\dramakit")
cfg = Config.load(Config.discover())
ctx = Context(cfg, ProjectStore.open(proj), Providers(cfg, REPO))

out.append("")
out.append("=== 新旧 header 对比（取一个镜头）===")
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            vp = sh.video_prompt or ""
            if MARKER not in vp:
                continue
            old_head = vp[:vp.find(MARKER)]
            plan = R.picture_plan(ctx, sh, sc)
            new_head = PG._r2v_header(plan)
            out.append(f"--- {sh.id} ---")
            out.append(f"  旧 header（{len(old_head)} 字符）:")
            for line in old_head.split("\n")[:7]:
                out.append(f"    {line[:170]}")
            out.append(f"  新 header（{len(new_head)} 字符）:")
            for line in new_head.split("\n")[:7]:
                out.append(f"    {line[:170]}")
            out.append(f"  图片数 旧={old_head.count('<Picture')} "
                       f"新={new_head.count('<Picture')}")
            Path(r"C:\Users\David\AppData\Local\Temp\opencode\hdrsample.txt"
                 ).write_text("\n".join(out), encoding="utf-8")
            print("wrote")
            raise SystemExit

Path(r"C:\Users\David\AppData\Local\Temp\opencode\hdrsample.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
