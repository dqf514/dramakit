"""What the episodes look like.

The title, the one line of what happens, and the hook at the end - the
three things a person decides to watch on.
"""
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore  # noqa: E402

ROOT = pathlib.Path(r"E:\dramakit\projects")
projs = [d for d in sorted(ROOT.iterdir())
         if d.is_dir() and (d / "project.json").exists()]
projs.sort(key=lambda d: (d / "project.json").stat().st_mtime, reverse=True)
p = projs[0]
store = ProjectStore.open(str(p))
proj = store.load()

print("  项目：", proj.meta.title or p.name, "  %d 集" % len(proj.episodes))
for ep in proj.episodes:
    print("")
    print("  第%2d集《%s》" % (ep.index, ep.title))
    print("     %s" % (ep.logline or ""))
    print("     钩子：%s" % (ep.hook or ""))
    print("     关键拍：%s" % "、".join(ep.key_beats or []))
