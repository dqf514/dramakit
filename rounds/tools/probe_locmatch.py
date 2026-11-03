"""Why each scene name misses its room, tried one by one.

The matcher has three chances - exact, then the base name without its
weather or time, then the closest - and it still refuses most scenes. The
docstring says the script names spots inside a room while the library
holds rooms, so this is the case the function was written for, and it is
not landing.

Every scene name is put through the real function and printed with what
came back, plus what each of the three steps saw, so the step that loses
it is visible rather than guessed at.
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import refs as R       # noqa: E402

out = []
cfg = Config.load(Config.discover())
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
store = ProjectStore.open(proj)
ctx = Context(cfg, store)

locs = list(ctx.project.locations or [])

out.append("=== 资产库里的房间 ===")
for loc in locs:
    out.append("  name=%r  norm=%r  base=%r"
               % (loc.name, R._norm(loc.name), R._norm(R._base(loc.name))))

out.append("")
out.append("=== 每个场景名的匹配过程 ===")
seen = set()
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        name = sc.location or ""
        if name in seen:
            continue
        seen.add(name)
        if not name:
            out.append("  (空场景名)")
            continue

        hit = R.find_location(ctx, name)
        n = R._norm(name)
        b = R._norm(R._base(name))

        exact = [l.name for l in locs if l.name == name]
        bynorm = [l.name for l in locs if R._norm(l.name) == n]
        bybase = [l.name for l in locs
                  if R._norm(l.name) and b
                  and (b in R._norm(l.name) or R._norm(l.name) in b)]

        best, bs = None, 0.0
        for l in locs:
            ln = R._norm(l.name)
            if not ln:
                continue
            s = R._run(b or n, ln) / max(1, min(len(b or n), len(ln)))
            if s > bs:
                best, bs = l, s

        out.append("  场景 %r" % name)
        out.append("      norm=%r  base=%r" % (n, b))
        out.append("      精确匹配 : %s" % (exact or "无"))
        out.append("      norm 匹配: %s" % (bynorm or "无"))
        out.append("      base 包含: %s" % (bybase or "无"))
        verdict = "过阈值" if bs >= 0.6 else "**低于 0.6，判无**"
        out.append("      最近似   : %s 分数=%.3f %s"
                   % (best.name if best else None, bs, verdict))
        out.append("      find_location -> %s"
                   % (hit.name if hit else "**None（判失败）**"))
        out.append("")

out.append("=== _run ===")
out.append(inspect.getsource(R._run))
out.append("=== _base ===")
out.append(inspect.getsource(R._base))
out.append("=== _norm ===")
out.append(inspect.getsource(R._norm))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\locmatch.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
