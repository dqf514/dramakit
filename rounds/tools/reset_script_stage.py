"""Clear the script stage of these episodes, so it is done again.

The merged stage writes the lines and the shots together.  The episodes
that were written by the old two stages have to be thrown away first,
or the new stage will skip them.
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
WHICH = [int(x) for x in (sys.argv[1:] or ["1"])]

store = ProjectStore.open(str(p))
proj = store.load()

print("  之前 %d 集" % len(proj.episodes))
for ep in proj.episodes:
    if ep.index not in WHICH:
        continue
    print("  第%d集《%s》 原来 %d 场 %d 镜"
          % (ep.index, ep.title, len(ep.scenes), ep.total_shots))
    ep.scenes = []
    for st in ("script", "storyboard", "promptgen"):
        ep.stage_status.pop(st, None)
    for sh in []:
        pass
    for sc in ep.scenes:
        for sh in sc.shots:
            sh.video_prompt = ""
store.save(proj)
print("  清好了：%s" % p.name)
