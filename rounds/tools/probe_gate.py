"""What the gate lets through now, on the shots it was refusing.

The rule was that a shot is not drawn without every reference, and the
room was one of them - so a book with more scene names than room art
refused most of itself. The first frame and the character sheets are the
ones that cannot be given up; the room is drawn into the first frame
already.

So the same shots are put through the same function, and what comes back
is compared with what came back before: what still blocks, and what now
merely goes without a room picture.
"""
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

out = []
blocked = 0
freed = 0
roomless = 0
total = 0
reasons: dict[str, int] = {}

for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for shot in sc.shots:
            total += 1
            missing = R.missing_references(ctx, shot, sc)
            if missing:
                blocked += 1
                for m in missing:
                    key = m.split(" ")[0][:24]
                    reasons[key] = reasons.get(key, 0) + 1
            else:
                loc = R.find_location(ctx, sc.location)
                if loc is None:
                    roomless += 1
                else:
                    freed += 1

out.append("=== 288 镜的门禁结果 ===")
out.append(f"  仍被拦下（真缺东西）: {blocked}")
out.append(f"  放行且有房间参考   : {freed}")
out.append(f"  放行但无房间参考   : {roomless}")
out.append(f"  合计 {blocked + freed + roomless} / {total}")

out.append("")
out.append("=== 仍被拦下的原因 ===")
if not reasons:
    out.append("  （无）")
for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
    out.append(f"  {v:>4}  {k}")

# a sample of the previously-refused scenes
out.append("")
out.append("=== 之前失败的场景，现在 ===")
seen = set()
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        if sc.location in seen:
            continue
        seen.add(sc.location)
        sh = sc.shots[0] if sc.shots else None
        if sh is None:
            continue
        m = R.missing_references(ctx, sh, sc)
        loc = R.find_location(ctx, sc.location)
        state = "拦下" if m else ("放行（无房间图）" if loc is None else "放行（有房间图）")
        out.append("  %-34s %s" % (sc.location, state))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\gate.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
