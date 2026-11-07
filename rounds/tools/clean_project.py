"""Take the project back to the book.

Everything that was made is taken away - the character sheets, the
cover, the scenes, the shots, the pictures, the clips, the subtitles -
and only the novel is left.  Then the pipeline starts again from the
beginning, which is the only way to see what the new stages really do.
"""
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(r"E:\dramakit\projects\穿成亿万总裁他前妻")
sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore  # noqa: E402

# what is made, and what is the book
MADE = ("characters", "covers", "episodes", "images", "locations",
        "video", "audio", "bgm", "subs", "tmp", "logs")
KEEP = "source"

store = ProjectStore.open(str(ROOT))
proj = store.load()

print("  之前：%d 集，%d 镜，%d 个角色" % (
    len(proj.episodes),
    sum(len(s.shots) for e in proj.episodes for s in e.scenes),
    len(proj.characters)))

# the made things go
for name in MADE:
    d = ROOT / name
    if d.exists():
        n = sum(1 for f in d.rglob("*") if f.is_file())
        shutil.rmtree(str(d), ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
        print("  清空 %-12s %d 个文件" % (name, n))

# the project itself: the book, and nothing else
src = ROOT / "source"
books = sorted(src.glob("*"))
keep = {}
for f in books:
    if f.is_file():
        keep[f.name] = f.stat().st_size
print("  小说原文留着：%s" % ", ".join(
    "%s(%d KB)" % (k, v // 1024) for k, v in keep.items()))

proj.episodes = []
proj.characters = []
proj.locations = []
proj.props = []
proj.stage_status = {}
proj.seasons = []
proj.meta.skills = {}
proj.meta.skills_recommended = False
proj.meta.last_run = {}
proj.meta.chosen_chapters = []
proj.art_direction.genre = ""
proj.art_direction.style = ""
proj.art_direction.style_prompt_prefix = ""
store.save(proj)
print("  project.json 也清干净了")
