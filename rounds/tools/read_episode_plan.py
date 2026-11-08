"""The episode plan, as a document.

Thirty episodes, each with its title, its one line, its hook and the
beats it has to hit - the thing a person reads before deciding to
watch.
"""
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore  # noqa: E402

ROOT = pathlib.Path(r"E:\dramakit\projects")
projs = [d for d in sorted(ROOT.iterdir())
         if d.is_dir() and (d / "project.json").exists()]
projs.sort(key=lambda d: (d / "project.json").stat().st_mtime, reverse=True)
store = ProjectStore.open(str(projs[0]))
proj = store.load()

out = ["# 《%s》分集计划" % (proj.meta.title or proj.meta.name), ""]
out.append("题材：%s" % proj.art_direction.genre)
out.append("画风：%s" % proj.art_direction.style)
out.append("共 %d 集" % len(proj.episodes))
out.append("")
for ep in proj.episodes:
    out.append("## 第%d集《%s》" % (ep.index, ep.title))
    out.append("")
    out.append("%s" % (ep.logline or ""))
    out.append("")
    out.append("**钩子**：%s" % (ep.hook or ""))
    out.append("")
    if ep.key_beats:
        out.append("关键拍：%s" % " / ".join(ep.key_beats))
        out.append("")

text = "\n".join(out)
p = pathlib.Path(store.root) / "分集计划.md"
p.write_text(text, encoding="utf-8")
print("  %d 集 → %s" % (len(proj.episodes), p))
