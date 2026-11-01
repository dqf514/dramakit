"""Do the skills describe themselves?

Thirty-seven skills need a one-line description each for a page that lets
a person choose between them. If the documents carry that already - a
frontmatter name and summary, or a first heading - the page reads it
rather than having it written by hand and left to rot.
"""
from pathlib import Path

out = []
root = Path(r"E:\dramakit\skills")

samples = [
    "short-drama-video-prompts",
    "short-drama-write",
    "screenwriting-theory/sw-character-conflict",
    "screenwriting-theory/ozu-screenplay-style",
    "short-drama-novel-analyze",
]
for name in samples:
    md = root / name / "SKILL.md"
    if not md.exists():
        out.append(f"=== {name} ===  不存在")
        continue
    text = md.read_text(encoding="utf-8", errors="replace")
    out.append(f"=== {name}  ({len(text):,} 字符) ===")
    out.append(text[:420])
    out.append("  ...")
    out.append("")

# how many have YAML frontmatter at all
front = 0
total = 0
for p in root.rglob("SKILL.md"):
    total += 1
    t = p.read_text(encoding="utf-8", errors="replace")
    if t.lstrip().startswith("---"):
        front += 1
out.append(f"=== 共 {total} 个 SKILL.md，其中 {front} 个以 --- 开头（YAML frontmatter）===")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\skillmeta.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
