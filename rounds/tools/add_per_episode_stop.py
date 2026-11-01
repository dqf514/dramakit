"""Ask once per episode, where the time actually goes.

A stop that only lands between stages is worth little: the script stage
alone is a hundred and fifty model calls, so waiting for the stage to end
means waiting for the batch to end. Every stage that walks the episodes
now asks before each one, which is where the minutes are - a stop takes
effect at the next episode rather than at the end of the run.

The check is one property read on a finished event, so a run nobody is
stopping pays nothing measurable for being stoppable.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit\\dramakit\\pipeline")
TARGETS = ("script", "storyboard", "promptgen", "voice", "visual", "compose")

total = 0
for name in TARGETS:
    p = ROOT / f"{name}.py"
    if not p.exists():
        print(f"  {name}.py 不存在，跳过")
        continue
    s = p.read_text(encoding="utf-8", errors="replace")
    if "check_stop" in s:
        print(f"  {name}.py 已有检查，跳过")
        continue

    lines = s.split("\n")
    out = []
    added = 0
    for line in lines:
        out.append(line)
        stripped = line.strip()
        # every episode loop is the same shape; the indent of the body is
        # the loop's own indent plus one level
        if stripped == "for ep in ctx.target_episodes():":
            indent = line[: len(line) - len(line.lstrip())]
            out.append(indent + "    ctx.check_stop()   # 一集一问：停止能在下一集生效")
            added += 1
    if added:
        p.write_text("\n".join(out), encoding="utf-8")
        print(f"  {name}.py: {added} 处逐集检查")
        total += added
    else:
        print(f"  {name}.py: 没找到逐集循环")

print(f"共加 {total} 处")
