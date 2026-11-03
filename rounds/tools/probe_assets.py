"""Find the pictures and recordings a real shot would use.

A render is the only test that cannot be run twice for free, so the inputs
have to be the ones the pipeline actually sends: the character's own sheet,
a first frame, and the voice the character speaks with. This reads the
project as the pipeline reads it, rather than listing directories by hand.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
root = Path(r"E:\dramakit\projects")
out.append("=== projects 下的目录 ===")
for d in sorted(root.iterdir()):
    if d.is_dir():
        out.append(f"  {d.name}")

# the project, found by name rather than typed (the shell mangles CJK)
proj = next((d for d in root.iterdir() if d.is_dir() and "志" in d.name), None)
if not proj:
    out.append("没找到带「志」的项目")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\assets.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

out.append("")
out.append(f"=== 项目 {proj.name} ===")
for d in sorted(proj.iterdir()):
    n = sum(1 for _ in d.rglob("*")) if d.is_dir() else 0
    out.append(f"  {d.name:12} {'dir' if d.is_dir() else 'file':4} {n:>5} 项")

out.append("")
out.append("=== characters ===")
ch = proj / "characters"
if ch.exists():
    for d in sorted(ch.iterdir())[:6]:
        if not d.is_dir():
            continue
        files = {f.name: f.stat().st_size for f in d.rglob("*") if f.is_file()}
        out.append(f"  {d.name}: {list(files)[:8]}")
else:
    out.append("  不存在")

out.append("")
out.append("=== images ===")
im = proj / "images"
if im.exists():
    fs = sorted([f for f in im.rglob("*") if f.is_file()],
                key=lambda f: f.stat().st_size, reverse=True)[:10]
    for f in fs:
        out.append(f"  {f.relative_to(proj)}  {f.stat().st_size/1024:.0f} KB")
else:
    out.append("  不存在")

out.append("")
out.append("=== audio（角色配音）===")
au = proj / "audio"
if au.exists():
    fs = [f for f in au.rglob("*") if f.is_file()][:12]
    for f in fs:
        out.append(f"  {f.relative_to(proj)}  {f.stat().st_size/1024:.0f} KB")
    if not fs:
        out.append("  空")
else:
    out.append("  不存在")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\assets.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
