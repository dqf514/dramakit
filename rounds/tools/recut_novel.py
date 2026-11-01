"""Re-cut the novel that came back with no chapters.

The book numbers its chapters 第X回, and the model guessed 第X章, so the
pattern matched nothing and the project had no table of contents. The
heading fallback is in place now; this runs the real catalog against the
real project and reports what comes out.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.pipeline import catalog
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

ROOT = Path(r"E:\dramakit\projects")
NAME = sys.argv[1] if len(sys.argv) > 1 else "九天灭魔传"

store = ProjectStore(ROOT / NAME)
cfg = Config()
ctx = Context(cfg, store)

src = ctx.project.meta.source_file
print("项目:", NAME)
print("源文件:", src)
print("切之前 meta.chapters:", len(ctx.project.meta.chapters or []))

res = catalog.run(ctx, src)

print()
print("结果:", res)
print("chapter_pattern:", ctx.project.meta.chapter_pattern)
print("卷:", ctx.project.meta.volumes)
print()
chs = ctx.project.meta.chapters or []
print("切出", len(chs), "章:")
for c in chs[:8]:
    print(f"  [{c.index:>2}] {c.title}  {c.chars} 字")
if len(chs) > 8:
    print("  ...")

vdir = ROOT / NAME / "source" / "volumes"
files = sorted(vdir.glob("*.txt"))
print()
print("volumes/ 里", len(files), "个文件")
