"""The episode as a screenplay.

The format is the repo's own: the scene heading, a stretch of action,
the lines, and the voices that are not spoken in the room.
"""
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.models import LineKind  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

ROOT = pathlib.Path(r"E:\dramakit\projects")
projs = [d for d in sorted(ROOT.iterdir())
         if d.is_dir() and (d / "project.json").exists()]
projs.sort(key=lambda d: (d / "project.json").stat().st_mtime, reverse=True)
store = ProjectStore.open(str(projs[0]))
proj = store.load()
WHICH = int(sys.argv[1]) if len(sys.argv) > 1 else 1

out = []
for ep in proj.episodes:
    if ep.index != WHICH:
        continue
    out.append("# 第%d集《%s》" % (ep.index, ep.title))
    out.append("")
    out.append("梗概：%s" % ep.logline)
    out.append("钩子：%s" % ep.hook)
    for sc in ep.scenes:
        out.append("")
        out.append("## 内 · %s · %s" % (sc.location, sc.time_of_day))
        out.append("")
        out.append(sc.summary or "")
        out.append("")
        for ln in sc.lines:
            who = ln.speaker
            if ln.kind == LineKind.MONOLOGUE:
                out.append("[VO] %s：%s" % (who, ln.text))
            elif ln.kind == LineKind.OFF_SCREEN:
                out.append("[OS] %s：%s" % (who, ln.text))
            elif ln.kind == LineKind.NARRATION:
                out.append("[旁白] %s" % ln.text)
            else:
                out.append("%s：%s" % (who, ln.text))

text = "\n".join(out)
p = pathlib.Path(r"E:\dramakit\rounds\tools\_screenplay.txt")
p.write_text(text, encoding="utf-8")
print("  %d 行 → %s" % (len(out), p))
