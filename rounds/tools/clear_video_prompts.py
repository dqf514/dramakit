"""The video prompts are written for the size the drama had.

The picture prompt does not name a size, but the video prompt does -
"the 9:16 vertical frame (1080x1920)" - so when the frame changes,
the video prompts have to be written again.
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

n = 0
for ep in proj.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            if sh.video_prompt:
                sh.video_prompt = ""
                sh.end_prompt = ""
                n += 1
store.save(proj)
print("  %s：清掉 %d 个视频提示词，等着重写" % (p.name, n))
