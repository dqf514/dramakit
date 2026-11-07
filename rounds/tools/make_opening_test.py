"""A look at the opening, without touching the drama.

The real project keeps its forty shots.  This is a copy with only the
first three of them, so the two 3090s make three clips instead of forty
and the opening can be looked at in a quarter of an hour.
"""
import pathlib
import shutil
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config  # noqa: E402
from dramakit.pipeline import make_context  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

SRC = pathlib.Path(r"E:\dramakit\projects\我死后-仙尊追悔莫及")
DST = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\opening_test")
N_SHOTS = 3

if DST.exists():
    shutil.rmtree(str(DST))
shutil.copytree(str(SRC), str(DST))
print("  复制到 %s" % DST)

store = ProjectStore.open(str(DST))
proj = store.load()
ep = proj.episodes[0]
sc = ep.scenes[0]
keep = sc.shots[:N_SHOTS]
print("  第1集：%d 场 %d 镜 → 只留第1场的前 %d 镜（%s）"
      % (len(ep.scenes), ep.total_shots, len(keep),
         "+".join(str(s.duration) for s in keep)))
ep.scenes = [sc]
sc.shots = keep
# the shots carry the lines they speak; the lines the other shots spoke
# are not spoken any more
spoken = set()
for s in keep:
    spoken |= set(s.line_indices or [])
sc.lines = [l for i, l in enumerate(sc.lines, 1) if i in spoken]
sc.beats = sc.beats[:max([max(s.beats or [0]) for s in keep] or [1])]
store.save(proj)

cfg = Config.load(Config.discover())
ctx = make_context(cfg, store)
print("  画幅 %s %sx%s" % (ctx.project.art_direction.aspect_ratio,
                          ctx.cfg.compose.width, ctx.cfg.compose.height))
