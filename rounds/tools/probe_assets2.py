"""Locate the project by its manifest, not by its name.

Directory names in CJK do not survive the trip through the shell and the
console - they come back as mojibake - so matching on a name fails even
when the directory is right there. A project is the thing that carries a
project.json, which is a fact about the file rather than about how the
name renders.

The assets a render needs are read the same way: what the pipeline would
hand the card for one shot, not a directory listing.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
root = Path(r"E:\dramakit\projects")

out.append("=== projects 下带 project.json 的目录 ===")
projects = []
for d in sorted(root.iterdir()):
    if not d.is_dir():
        continue
    if (d / "project.json").exists():
        projects.append(d)
        raw = json.loads((d / "project.json").read_text(encoding="utf-8"))
        title = raw.get("title") or raw.get("name") or "?"
        cps = " ".join(f"U+{ord(c):04X}" for c in d.name)
        out.append(f"  {d.name}   (码点: {cps})")
        out.append(f"      title={title!r}  keys={sorted(raw)[:8]}")
if not projects:
    out.append("  一个都没有")

# assets: every project dir's own folders
for proj in projects:
    out.append("")
    out.append(f"=== {proj.name} 的资产 ===")
    for sub in ("characters", "images", "audio", "video", "episodes"):
        p = proj / sub
        if not p.exists():
            out.append(f"  {sub}: 不存在")
            continue
        files = [f for f in p.rglob("*") if f.is_file()]
        out.append(f"  {sub}: {len(files)} 个文件")
        for f in files[:6]:
            out.append(f"      {f.relative_to(proj)}  {f.stat().st_size/1024:.0f} KB")
        if len(files) > 6:
            out.append(f"      ... 还有 {len(files)-6} 个")

# and the loose asset folders sitting directly in projects/
out.append("")
out.append("=== projects/ 根下散落的资产目录 ===")
for sub in ("characters", "images", "audio", "video"):
    p = root / sub
    if p.exists():
        files = [f for f in p.rglob("*") if f.is_file()]
        out.append(f"  {sub}: {len(files)} 个文件")
        for f in files[:5]:
            out.append(f"      {f.relative_to(root)}  {f.stat().st_size/1024:.0f} KB")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\assets2.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
