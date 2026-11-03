"""Whether anyone speaks in this project without being in the cast.

The other project had a speaker with no character entry, and the shots
she was in refused to render because a person with no sheets is a person
the gate will not accept. The same thing can happen here, and it is
cheaper to find it now than to read the failures out of the log later.

So every speaker, every name on a shot, and every name in the cast are
put side by side, and the ones that match nothing are listed.
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

REPO = Path(r"E:\dramakit")
proj = REPO / "projects" / "星际骷髅兵"
cfg = Config.load(Config.discover())
ctx = Context(cfg, ProjectStore.open(proj), Providers(cfg, REPO))

out = []
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))

cast = {c.name for c in (ctx.project.characters or [])}
aliases = {}
for c in (ctx.project.characters or []):
    for a in (c.aliases or []):
        aliases[a] = c.name
out.append(f"=== 角色表 {len(cast)} 人 ===")
for c in (ctx.project.characters or []):
    out.append(f"  {c.name:14} role={c.role:10} aliases={c.aliases or []}")

speakers: dict[str, int] = {}
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for ln in sc.lines:
            speakers[ln.speaker] = speakers.get(ln.speaker, 0) + 1

out.append("")
out.append("=== 说话人 ===")
unknown = []
for sp, n in sorted(speakers.items(), key=lambda x: -x[1]):
    if sp in cast:
        out.append(f"  {sp:14} {n:>4} 句  ✓")
    elif sp in aliases:
        out.append(f"  {sp:14} {n:>4} 句  = {aliases[sp]}（别名）")
    else:
        unknown.append((sp, n))
        out.append(f"  {sp:14} {n:>4} 句  **不在角色表**")

# names on shots
shot_names: dict[str, int] = {}
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            for nm in (sh.characters or []):
                shot_names[nm] = shot_names.get(nm, 0) + 1
out.append("")
out.append("=== 镜头上的角色名 ===")
for nm, n in sorted(shot_names.items(), key=lambda x: -x[1]):
    mark = "✓" if nm in cast else ("=别名" if nm in aliases else "**不在角色表**")
    out.append(f"  {nm:14} {n:>4} 镜  {mark}")

out.append("")
out.append("=== 门禁会拦下谁 ===")
blocked = 0
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            m = [x for x in R.missing_references(ctx, sh, sc)
                 if "首帧" not in x]
            if m:
                blocked += 1
                if blocked <= 8:
                    out.append(f"  {sh.id}: {m}")
out.append(f"  合计被拦 {blocked} 镜（不含首帧等待）")

# the score shots and other outputs
out.append("")
out.append("=== 配乐镜头（音乐垫底）===")
md = proj / "music"
if md.exists():
    for f in sorted(md.iterdir()):
        out.append(f"  {f.name:28} {f.stat().st_size/1024:8.0f} KB")
else:
    out.append("  （还没有）")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\cast_check.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
