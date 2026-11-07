"""Clear the script stage of these episodes, so it is done again.

The merged stage writes the lines and the shots together.  The episodes
that were written by the old two stages have to be thrown away first,
or the new stage will skip them.
"""
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.project import ProjectStore

PROJ = r"E:\dramakit\projects\穿成亿万总裁他前妻"
WHICH = [int(x) for x in (sys.argv[1:] or ["1"])]

store = ProjectStore.open(PROJ)
proj = store.load()
for ep in proj.episodes:
    if ep.index not in WHICH:
        continue
    print("第%d集《%s》 原来 %d 场 %d 镜"
          % (ep.index, ep.title, len(ep.scenes), ep.total_shots))
    ep.scenes = []
    for st in ("script", "storyboard"):
        ep.stage_status.pop(st, None)
store.save(proj)
print("清好了")
