"""Take the project back to the book.

Everything that was made is taken away - the character sheets, the
cover, the scenes, the shots, the pictures, the clips, the subtitles -
and only the novel is left.  Then the pipeline starts again from the
beginning, which is the only way to see what the new stages really do.
"""
import pathlib
import shutil
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore  # noqa: E402

ROOT = pathlib.Path(r"E:\dramakit\projects")
projs = [d for d in sorted(ROOT.iterdir())
         if d.is_dir() and (d / "project.json").exists()]
projs.sort(key=lambda d: (d / "project.json").stat().st_mtime, reverse=True)
p = projs[0]
if len(sys.argv) > 1:
    p = next(d for d in projs if sys.argv[1] in d.name)

# what is made, and what is the book
MADE = ("characters", "covers", "episodes", "images", "locations",
        "video", "audio", "bgm", "subs", "tmp", "logs", "qc", "nle")
KEEP = "source"

store = ProjectStore.open(str(p))
proj = store.load()

print("  项目：%s" % p.name)
print("  之前：%d 集，%d 镜，%d 个角色"
      % (len(proj.episodes),
         sum(len(s.shots) for e in proj.episodes for s in e.scenes),
         len(proj.characters)))

for name in MADE:
    d = p / name
    if d.exists():
        n = sum(1 for f in d.rglob("*") if f.is_file())
        shutil.rmtree(str(d), ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
        print("  清空 %-12s %d 个文件" % (name, n))

# the loose files that are not the book either
for f in list(p.iterdir()):
    if f.is_file() and f.name not in ("project.json", ".progress.json"):
        print("  删掉 %s" % f.name)
        f.unlink()

src = p / "source"
books = sorted(f.name for f in src.iterdir() if f.is_file())
print("  小说原文留着：%s" % "、".join(books))

proj.episodes = []
proj.characters = []
proj.locations = []
proj.props = []
proj.seasons = []
proj.stage_status = {}
proj.meta.skills = {}
proj.meta.skills_recommended = False
proj.meta.last_run = {}
proj.meta.chosen_chapters = []
proj.meta.segmented_chapters = []
proj.art_direction.genre = ""
proj.art_direction.style = ""
proj.art_direction.style_prompt_prefix = ""
store.save(proj)
print("  project.json 也清干净了")
