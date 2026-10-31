"""Bring the episodes that were prepared in a copy back into the project.

Episodes two and three were re-shot in a copy while episode one was being
drawn - the copy had the new segments, the new room assets and the new
prompts.  This copies those two episodes (and the rooms they need) into the
project the pipeline renders from.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

src_root = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\\tmp\\ep23")
dst_root = Path(sys.argv[2] if len(sys.argv) > 2
                else r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
eps = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [2, 3]

src = ProjectStore(src_root).load()
dst = ProjectStore(dst_root)
proj = dst.load()

# the rooms the new episodes need
have = {l.name for l in proj.locations}
for loc in src.locations:
    if loc.name in have:
        continue
    proj.locations.append(loc)
    s = src_root / "locations" / loc.name
    d = dst_root / "locations" / loc.name
    if s.exists():
        shutil.copytree(s, d, dirs_exist_ok=True)
        print(f"  房间资产搬过来: {loc.name}")

# the episodes
for ep in src.episodes:
    if ep.index not in eps:
        continue
    old = next((e for e in proj.episodes if e.index == ep.index), None)
    if old is None:
        proj.episodes.append(ep)
    else:
        pos = proj.episodes.index(old)
        proj.episodes[pos] = ep
    print(f"  第{ep.index}集《{ep.title}》搬过来："
          f"{ep.total_shots} 个片段")

# the pictures that came with them
for sub in ("images", "characters", "locations"):
    s = src_root / sub
    if not s.exists():
        continue
    for f in s.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(src_root)
        d = dst_root / rel
        if not d.exists():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d)

dst.save(proj)
print(f"已保存到 {dst_root}")
