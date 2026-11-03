"""Which folder is the casting stage drawing into?

The local card is at a hundred percent and the count of pictures is not
moving, which means either nothing new is being written or it is going
somewhere the counter does not look. This lists what was actually written
in the last few minutes, and where the characters that have no pictures
yet would put theirs.
"""
import json
import time
from pathlib import Path

root = Path(r"E:\dramakit\projects\魔兽世界")
out = []

recent = sorted(
    ((f.stat().st_mtime, f) for f in root.rglob("*")
     if f.is_file() and time.time() - f.stat().st_mtime < 330),
    reverse=True)
out.append(f"=== 最近 5 分半改动的文件 {len(recent)} 个 ===")
for t, f in recent[:25]:
    out.append(f"  {time.strftime('%H:%M:%S', time.localtime(t))}  "
               f"{str(f.relative_to(root))[:64]:<64} {f.stat().st_size // 1024} KB")

out.append("")
d = json.loads((root / "project.json").read_text(encoding="utf-8"))
out.append("=== 模型里的角色（缺图的会被画）===")
for c in d.get("characters", []):
    n = len(c.get("ref_images") or [])
    out.append(f"  {c.get('name'):<22} 图={n}  voice_ref={'有' if c.get('voice_ref') else '无'}")

out.append("")
out.append("=== 磁盘目录结构 ===")
cdir = root / "characters"
if cdir.exists():
    for sub in sorted(cdir.iterdir()):
        if sub.is_dir():
            files = [f.name for f in sub.iterdir() if f.is_file()]
            out.append(f"  {sub.name}/  {len(files)} 个: {sorted(files)}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\where.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
