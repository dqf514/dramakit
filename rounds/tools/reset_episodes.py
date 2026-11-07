"""Cut the episodes again, from the new chapters.

The chapters were split wrong once - the download site's front matter
was counted as a chapter - so the episodes are cut again from the
chapters that are right now.
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

print("  之前 %d 集" % len(proj.episodes))
proj.episodes = []
for st in ("segment", "script", "storyboard", "promptgen", "visual"):
    proj.stage_status.pop(st, None)
proj.meta.segmented_chapters = []
proj.meta.last_run = {}
store.save(proj)
print("  清好了：%s" % p.name)
