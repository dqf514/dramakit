"""Where the skill rules live, and how much of them there is.

The prompt stage ships ten thousand characters of rules with every video
call, and they come from somewhere on disk. This lists that place: what
files exist, how big each is, and how the loader decides what to send.
"""
from pathlib import Path

out = []
root = Path(r"E:\dramakit\skills")

out.append("=== skills/ 结构 ===")
if not root.exists():
    out.append("  不存在")
else:
    total = 0
    files = [f for f in sorted(root.rglob("*")) if f.is_file()]
    for f in files:
        sz = f.stat().st_size
        total += sz
        out.append(f"  {str(f.relative_to(root)):<56} {sz:>8,} B")
    out.append(f"  {'-' * 56}")
    out.append(f"  {'合计 ' + str(len(files)) + ' 个文件':<56} {total:>8,} B")

out.append("")
out.append("=== 谁在读它们 ===")
for f in Path(r"E:\dramakit\dramakit").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    if "skills" in t and ("loader" in t or "for_stage" in t):
        for n, line in enumerate(t.split("\n"), 1):
            if "for_stage" in line or "skills import" in line:
                out.append(f"  {f.name}:{n}  {line.strip()[:130]}")

out.append("")
out.append("=== SkillsConfig ===")
import re
cfg = Path(r"E:\dramakit\dramakit\config.py").read_text(encoding="utf-8")
m = re.search(r"class SkillsConfig.*?(?=\nclass )", cfg, re.S)
out.append(m.group(0) if m else "  (未找到)")

out.append("")
out.append("=== 配置里的 skills 段 ===")
y = Path(r"E:\dramakit\config\default.yaml").read_text(encoding="utf-8")
i = y.find("skills:")
out.append(y[i:i + 700] if i > 0 else "  (无 skills 段)")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\skills.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
