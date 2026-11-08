"""The whole drama, as one document.

Every episode, in the screenplay's own shape: the scene heading, a
stretch of action, what is said out loud, and the voice that is not
spoken in the room.
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

out = []
out.append("# 《%s》" % (proj.meta.title or proj.meta.name))
out.append("")
out.append("题材：%s" % proj.art_direction.genre)
out.append("画风：%s" % proj.art_direction.style)
out.append("画幅：%s %sx%s" % (proj.art_direction.aspect_ratio,
                              proj.art_direction.frame_width,
                              proj.art_direction.frame_height))
out.append("集数：%d" % len(proj.episodes))
out.append("")
out.append("---")
out.append("")

for ep in proj.episodes:
    out.append("# 第%d集《%s》" % (ep.index, ep.title))
    out.append("")
    out.append("%s" % (ep.logline or ""))
    out.append("")
    out.append("**钩子**：%s" % (ep.hook or ""))
    out.append("")
    if ep.key_beats:
        out.append("关键拍：%s" % " / ".join(ep.key_beats))
        out.append("")
    if not ep.scenes:
        out.append("*（这一集还没写）*")
        out.append("")
        out.append("---")
        out.append("")
        continue
    for sc in ep.scenes:
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
        out.append("")
    out.append("---")
    out.append("")

text = "\n".join(out)
p = pathlib.Path(store.root) / "剧本.md"
p.write_text(text, encoding="utf-8")
done = sum(1 for e in proj.episodes if e.scenes)
print("  %d/%d 集 → %s" % (done, len(proj.episodes), p))
