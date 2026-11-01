"""Did the analysis read three chapters, or four hundred and eighty-five?

Segment has not run, so the cut cannot be inspected yet - but the analysis
has, and what it was given is decided by code, not by mood. This runs the
same path the analysis ran and reports how much of the book it would have
read, then checks the model was not asked for the rest.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.pipeline.analyze import _canon_block, _season_text
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

ROOT = Path(r"E:\dramakit\projects")
slug = next(d.name for d in sorted(ROOT.iterdir())
            if (d / "project.json").exists() and
            json.loads((d / "project.json").read_text(encoding="utf-8"))
            .get("meta", {}).get("chosen_chapters"))

store = ProjectStore.open(ROOT / slug)
ctx = Context(Config.load(Config.discover()), store)

out = [f"项目: {slug}"]
out.append(f"  season_index: {ctx.season_index}  scoped: {ctx.season_scoped}")
out.append(f"  season_chapters(): {ctx.season_chapters()}")
out.append(f"  chosen_chapters  : {ctx.project.meta.chosen_chapters}")
out.append("")

# point at the season the run is on, the way the run did
s = ctx.project.season(1)
if s is not None:
    ctx.use_season(1)
    out.append(f"  打开第1季后 season_chapters(): {ctx.season_chapters()}")

text, chapters = _season_text(ctx)
total = sum(f.stat().st_size for f in (ROOT / slug / "source" / "volumes").glob("*.txt"))
out.append("")
out.append("=== analyze 实际读到的 ===")
out.append(f"  字符数     : {len(text):,}")
out.append(f"  章节块     : {len(chapters)}")
out.append(f"  各章字数   : {[len(c['body']) for c in chapters]}")
out.append(f"  占全书比例 : {len(text) * 100 / max(total, 1):.2f}%  （全书 {total:,} 字节）")
out.append(f"  开头 80 字 : {text[:80]!r}")

out.append("")
out.append("=== 注入的前情摘要 ===")
cb = _canon_block(ctx)
out.append(f"  长度 {len(cb)} 字")
out.append("  " + (cb[:220].replace("\n", " / ") if cb else "（空——首季没有前情，正确）"))

# the cast it produced, and where the pictures are going
out.append("")
d = json.loads((ROOT / slug / "project.json").read_text(encoding="utf-8"))
chars = d.get("characters") or []
out.append(f"=== 分析产出 ===")
out.append(f"  角色 {len(chars)} 个: {[c.get('name') for c in chars]}")
cdir = ROOT / slug / "characters"
if cdir.exists():
    imgs = [f for f in cdir.rglob("*") if f.suffix.lower() in (".png", ".jpg")]
    out.append(f"  参考图 {len(imgs)} 张")
    for f in sorted(imgs)[:8]:
        out.append(f"    {f.relative_to(cdir)}  {f.stat().st_size // 1024} KB")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\analysis_scope.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
