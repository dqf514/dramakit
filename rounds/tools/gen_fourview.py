"""Replace each character's five reference pictures with one four-view sheet.

The plan hands the model two pictures per person - a face and a sheet of
bodies - and the sheet now carries both, so it has to hand over one. Until
the folders hold a single sheet the plan goes on finding the old face
picture and building the old sheet, and the code change does not show.

The old records are cleared first: generate_refs appends, so a character
left holding five entries would come out with six. The files themselves
are left on disk - nothing reads them once the record does not point at
them, and a rerun that wants the old look back can find it.

One context, one save. A second context reading the project while this
one holds it writes back over whatever the first one did, which is how
the anchor and the pictures ended up registered in one run and empty in
the next.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.providers import Providers      # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import character as CH # noqa: E402

REPO = Path(r"E:\dramakit")
out = []

cfg = Config.load(Config.discover())
proj = next(d for d in (REPO / "projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
store = ProjectStore.open(proj)
ctx = Context(cfg, store, Providers(cfg, REPO))

out.append(f"=== 配置 ===")
out.append(f"  ref_views = {cfg.characters.ref_views}")
out.append(f"  四视图尺寸 = {cfg.characters.ref_four_width} x "
           f"{cfg.characters.ref_four_height}")
out.append(f"  生成开关 = {cfg.characters.generate_refs}")

chars = list(ctx.project.characters)
out.append(f"\n=== {len(chars)} 个角色 ===")

made_total = 0
for c in chars:
    t0 = time.time()
    # Clear first: generate_refs appends, so five entries left in place
    # come back out as five plus the new one.
    old = list(c.ref_images)
    c.ref_images = []
    c.ref_sheet = ""
    try:
        made = CH.generate_refs(ctx, c)
    except Exception as e:  # noqa: BLE001
        out.append(f"  {c.name}: **失败** {type(e).__name__}: {str(e)[:160]}")
        c.ref_images = old          # put it back rather than lose it
        continue
    made_total += made
    files = [p.name for p in (proj / "characters" / c.name).iterdir()] \
        if (proj / "characters" / c.name).exists() else []
    out.append(f"  {c.name}: 生成 {made} 张，记录 {len(c.ref_images)} 条 "
               f"({time.time()-t0:.0f}s)  目录={files}")

ctx.save()
out.append(f"\n合计生成 {made_total} 张")

# --- read it back the way a fresh process would ------------------------
again = ProjectStore.open(proj).load()
out.append("\n=== 重新读盘 ===")
for c in again.characters[:4]:
    out.append(f"  {c.name}: ref_images={c.ref_images}  ref_sheet={c.ref_sheet!r}")
out.append(f"  ... 共 {len(again.characters)} 个角色")

# --- does the plan now give one picture per person? --------------------
from dramakit.pipeline import refs as R   # noqa: E402
ctx2 = Context(cfg, ProjectStore.open(proj), Providers(cfg, REPO))
out.append("\n=== picture_plan 重新统计 ===")
shape: dict[tuple, int] = {}
sample = None
for ep in ctx2.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            plan = R.picture_plan(ctx2, sh, sc)
            key = (len(plan), len(sh.characters or []))
            shape[key] = shape.get(key, 0) + 1
            if sample is None and (sh.characters or []):
                sample = (sh.id, plan)
for (n, k), v in sorted(shape.items()):
    out.append(f"  {n} 图 / {k} 人: {v} 镜")

if sample:
    sid, plan = sample
    out.append(f"\n=== 样本 {sid} ===")
    for i, (p, role, kind) in enumerate(plan, 1):
        out.append(f"  <Picture {i}> [{kind}] {Path(p).name}")
        out.append(f"        {role[:130]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\genfour.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
