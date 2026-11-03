"""What a fuller separator list would recover, counted.

The splitter that reduces a spot to its room knows about a middle dot but
not about the full stop this book uses to join a place to its weather, so
the weather stays in the room name and nothing in the library contains it.
Adding the character is the obvious repair - but it is only worth doing if
it is the whole story: some of these scenes are plainly different places,
and no amount of punctuation will make a forest floor into a camp.

So each scene name is tried twice, once as the code does now and once with
the extra separator, and the two are counted. Names are printed as code
points, because the console cannot be trusted to show them.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import refs as R       # noqa: E402

cfg = Config.load(Config.discover())
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
ctx = Context(cfg, ProjectStore.open(proj))
locs = list(ctx.project.locations or [])

OLD_SPLIT = r"[·？\-|—/]"
NEW_SPLIT = r"[·？。！\-|—/、,，]"


def base_v2(s: str) -> str:
    return re.split(NEW_SPLIT, s or "", maxsplit=1)[0].strip()


out = []
out.append("=== 资产库（码点）===")
for l in locs:
    cps = " ".join("%04X" % ord(c) for c in l.name)
    out.append("  %s   [%s]" % (l.name, cps))

out.append("")
out.append("=== 每个场景名：现在 vs 加分隔符 ===")
seen: dict[str, int] = {}
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        seen[sc.location or ""] = seen.get(sc.location or "", 0) + len(sc.shots)

ok_now = ok_new = 0
shots_now = shots_new = 0
rows = []
for name, nshots in sorted(seen.items(), key=lambda x: -x[1]):
    if not name:
        continue
    now = R.find_location(ctx, name) is not None
    # the same function, with the fuller splitter
    orig = R._base
    R._base = base_v2
    try:
        new = R.find_location(ctx, name) is not None
    finally:
        R._base = orig
    rows.append((name, nshots, now, new))
    shots_now += nshots if now else 0
    shots_new += nshots if new else 0
    ok_now += 1 if now else 0
    ok_new += 1 if new else 0

for name, nshots, now, new in rows:
    cps = " ".join("%04X" % ord(c) for c in name)
    mark = ("现在OK" if now else "现在失败")
    if new and not now:
        mark += " → **加了分隔符后 OK**"
    elif not new:
        mark += " → 仍失败（不是分隔符的问题）"
    out.append("  %-3d 镜  %s" % (nshots, mark))
    out.append("        [%s]" % cps)

out.append("")
out.append("=== 汇总 ===")
out.append("  场景名总数 %d，现在匹配 %d，加分隔符后 %d" % (len(rows), ok_now, ok_new))
out.append("  镜头可渲染 %d / %d，加分隔符后 %d" % (shots_now, sum(n for _, n, _, _ in rows), shots_new))

still = [n for n, _s, now, new in rows if not new]
out.append("")
out.append("=== 加了分隔符仍失败的场景（这些是真没资产）===")
for n in still:
    out.append("  %r  %d 镜" % (n, seen[n]))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\fixcalc.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
