"""One character, one picture - and the plan numbers it the way it is sent.

The sheet now holds the face and the three bodies in a single image, so
the plan has to hand over one picture per person instead of two: two would
give the model the same file under two numbers, and the prompt, which
names its pictures by position, would describe one of them as a face
filling the frame when it is a whole sheet.

This reads the plan back for a sample of shots across the cast sizes, and
prints what the prompt header would say about each picture - which is the
part that has to agree with what is actually sent.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.providers import Providers      # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import refs as R       # noqa: E402
from dramakit.pipeline import promptgen as PG  # noqa: E402

REPO = Path(r"E:\dramakit")
out = []
cfg = Config.load(Config.discover())
proj = next(d for d in (REPO / "projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
ctx = Context(cfg, ProjectStore.open(proj), Providers(cfg, REPO))

out.append(f"=== 配置 ===")
out.append(f"  ref_views       = {cfg.characters.ref_views}")
out.append(f"  ref_four 尺寸   = {cfg.characters.ref_four_width} x "
           f"{cfg.characters.ref_four_height}")
out.append(f"  ref_body 尺寸   = {cfg.characters.ref_body_width} x "
           f"{cfg.characters.ref_body_height}")

# --- what each character's folder now holds ----------------------------
out.append("")
out.append("=== 角色目录（旧的5张还在，新的四视图尚未生成）===")
for d in sorted((proj / "characters").iterdir())[:4]:
    if d.is_dir():
        out.append(f"  {d.name}: {[f.name for f in sorted(d.iterdir())]}")

# --- the plan, by cast size --------------------------------------------
out.append("")
out.append("=== picture_plan（按角色数分组）===")
seen_shape: dict[tuple, int] = {}
samples = []
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            plan = R.picture_plan(ctx, sh, sc)
            nchar = len(sh.characters or [])
            key = (len(plan), nchar)
            seen_shape[key] = seen_shape.get(key, 0) + 1
            if len(samples) < 4 and (nchar, len(plan)) not in [
                    (s[0], s[1]) for s in samples]:
                samples.append((nchar, len(plan), sh.id, plan))

for (n, k), v in sorted(seen_shape.items()):
    out.append(f"  {n} 图 / {k} 人: {v} 镜")

out.append("")
out.append("=== 样本：提示词会怎么描述这些图 ===")
for nchar, nplan, sid, plan in samples[:3]:
    out.append(f"  {sid}（{nchar} 人，{nplan} 图）")
    for i, (p, role, kind) in enumerate(plan, 1):
        out.append(f"    <Picture {i}> [{kind}] {Path(p).name}: {role[:90]}")
    # the header the prompt would get
    try:
        hdr = PG._r2v_header(plan)
        first = hdr.split("\n")[0]
        out.append(f"    header 首行: {first[:110]}")
    except Exception as e:  # noqa: BLE001
        out.append(f"    header 生成失败: {e}")
    out.append("")

# --- the change in picture count ---------------------------------------
out.append("=== 每角色图片数 ===")
out.append("  旧: 2 张（face + 三视图合成 sheet）")
out.append("  新: 1 张（四视图）")
out.append("  → 每镜参考图减少 角色数 张")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\fourview.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
