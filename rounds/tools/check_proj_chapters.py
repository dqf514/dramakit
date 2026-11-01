"""Does a project have its chapters?"""
import json
import sys
from pathlib import Path

root = Path(r"E:\\dramakit\\projects")
name = sys.argv[1] if len(sys.argv) > 1 else "魔兽世界"
p = root / name / "project.json"
if not p.exists():
    print(f"  项目不存在: {name}")
    print("  现有项目:", ", ".join(d.name for d in root.iterdir() if d.is_dir()))
    sys.exit(0)

d = json.loads(p.read_text(encoding="utf-8"))
meta = d.get("meta", {})
print(f"  项目: {meta.get('name')}")
print(f"  小说: {meta.get('source_file')}")
print(f"  卷: {meta.get('volumes')}")
chs = meta.get("chapters") or []
print(f"  章: {len(chs)} 个")
for c in chs[:5]:
    print(f"    第{c.get('index')}章 {c.get('title')}  {c.get('chars')}字  {c.get('file')}")

# and the chapter files on disk
vdir = root / name / "source" / "volumes"
if vdir.exists():
    files = list(vdir.glob("*.txt"))
    print(f"  source/volumes/ 里有 {len(files)} 个文件")
else:
    print("  source/volumes/ 不存在（说明没切分过）")
