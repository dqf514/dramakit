"""How many pictures a shot actually gets, and how many people are in it.

Cutting the reference list saves about a tenth of a second per picture,
which over a whole series is hours - but the list is numbered, and the
prompts already written name their pictures by position, so a cut has to
know what it is cutting. A shot with one person loses its room; a shot
with three loses two of the three faces, which is the thing the
references exist to hold.

So both are counted across every shot: the pictures the plan produces,
and the cast in the shot - which is what says whether a flat cut of three
is affordable at all.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.providers import Providers      # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import refs as R       # noqa: E402

REPO = Path(r"E:\dramakit")
cfg = Config.load(Config.discover())
proj = next(d for d in (REPO / "projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
ctx = Context(cfg, ProjectStore.open(proj), Providers(cfg, REPO))

out = []
dist: dict[int, int] = {}
cast: dict[int, int] = {}
combo: dict[tuple, int] = {}
kinds_total: dict[str, int] = {}
shots = 0
would_lose_face = 0
would_lose_views = 0

for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            plan = R.picture_plan(ctx, sh, sc)
            n = len(plan)
            k = len(sh.characters or [])
            shots += 1
            dist[n] = dist.get(n, 0) + 1
            cast[k] = cast.get(k, 0) + 1
            combo[(n, k)] = combo.get((n, k), 0) + 1
            for _p, _r, kind in plan:
                kinds_total[kind] = kinds_total.get(kind, 0) + 1
            if n > 3:
                # what a cut to three would drop, given the order
                kept = plan[:3]
                kinds_kept = {kind for _p, _r, kind in kept}
                if "character" in {kind for _p, _r, kind in plan} and \
                        "character" not in kinds_kept:
                    would_lose_face += 1
                if n >= 4 and plan[3][2] == "character" and \
                        len([1 for _p, _r, kind in plan if kind == "character"]) \
                        > len([1 for _p, _r, kind in kept if kind == "character"]):
                    would_lose_views += 1

out.append(f"=== {shots} 镜的参考图数量分布 ===")
for n in sorted(dist):
    out.append(f"  {n} 张: {dist[n]:>4} 镜  ({dist[n]/shots*100:.0f}%)")

out.append("")
out.append("=== 镜内角色数分布 ===")
for k in sorted(cast):
    out.append(f"  {k} 个角色: {cast[k]:>4} 镜")

out.append("")
out.append("=== 各类参考图总数 ===")
for k, v in sorted(kinds_total.items(), key=lambda x: -x[1]):
    out.append(f"  {k:10} {v:>4}")

out.append("")
out.append("=== 裁到 3 张的后果 ===")
over3 = sum(v for n, v in dist.items() if n > 3)
out.append(f"  超过 3 张的镜头: {over3} ({over3/shots*100:.0f}%)")
out.append(f"  其中会丢掉全部人物参考的: {would_lose_face}")
out.append(f"  其中会丢掉三视图的: {would_lose_views}")

out.append("")
out.append("=== 组合（参考图数, 角色数）===")
for (n, k), v in sorted(combo.items()):
    out.append(f"  {n} 图 / {k} 人: {v} 镜")

# what a cut of 3 keeps, by shape
out.append("")
out.append("=== 裁到 3 时保留的是什么（按顺序前 3 项）===")
shapes: dict[tuple, int] = {}
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            plan = R.picture_plan(ctx, sh, sc)
            key = tuple(kind for _p, _r, kind in plan[:3])
            shapes[key] = shapes.get(key, 0) + 1
for key, v in sorted(shapes.items(), key=lambda x: -x[1]):
    out.append(f"  {key}: {v} 镜")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\refcount.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
