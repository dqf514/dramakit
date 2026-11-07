"""What novel is this?

The name, how long it is, how it is divided, and the first pages -
because the adaptation starts with knowing what kind of story it is.
"""
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore  # noqa: E402

ROOT = pathlib.Path(r"E:\dramakit\projects")
projs = [d for d in sorted(ROOT.iterdir())
         if d.is_dir() and d.name != "_trash"
         and (d / "project.json").exists()]
projs.sort(key=lambda d: (d / "project.json").stat().st_mtime, reverse=True)
p = projs[0]
print("=== 项目 ===")
print("  名字：", p.name)

src = p / "source"
for f in sorted(src.glob("*")):
    if f.is_file():
        print("  源文件：%s  %.1f KB" % (f.name, f.stat().st_size / 1024))

store = ProjectStore.open(str(p))
proj = store.load()
print("  集数：%d   角色：%d   场景：%d" % (
    len(proj.episodes), len(proj.characters), len(proj.locations)))
if proj.art_direction.genre:
    print("  题材：", proj.art_direction.genre)

cleaned = src / "cleaned.txt"
if cleaned.exists():
    text = cleaned.read_text(encoding="utf-8", errors="replace")
    print("\n=== 正文 %d 字 ===" % len(text))
    print(text[:3000])
