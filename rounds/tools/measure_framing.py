"""What the shot list looks like.

A drama is not one framing repeated: it opens wide, cuts in for the
line, goes over the shoulder for the answer, comes back for the
reaction, and shows the object the line is about.
"""
import collections
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore  # noqa: E402

OUT = open(r"E:\dramakit\rounds\tools\_framing.txt", "w", encoding="utf-8")


def say(*a):
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


ROOT = pathlib.Path(r"E:\dramakit\projects")
projs = [d for d in sorted(ROOT.iterdir())
         if d.is_dir() and (d / "project.json").exists()]
projs.sort(key=lambda d: (d / "project.json").stat().st_mtime, reverse=True)
store = ProjectStore.open(str(projs[0]))
proj = store.load()

for ep in proj.episodes:
    shots = [sh for sc in ep.scenes for sh in sc.shots]
    if not shots:
        continue
    size = collections.Counter(sh.shot_type.value for sh in shots)
    angle = collections.Counter((sh.angle or "").strip() for sh in shots)
    combo = collections.Counter((sh.shot_type.value, (sh.angle or "").strip())
                                for sh in shots)
    say("== 第%d集《%s》 %d 镜" % (ep.index, ep.title, len(shots)))
    say("   景别：%s" % "  ".join("%s %d" % (k, v)
                                for k, v in size.most_common()))
    say("   角度：%s" % "  ".join("%s %d" % (k, v)
                                for k, v in angle.most_common()))
    say("   组合前五：%s" % "  ".join(
        "%s/%s x%d" % (k[0], k[1], v) for k, v in combo.most_common(5)))
    same = sum(1 for a, b in zip(shots, shots[1:])
               if (a.shot_type.value, a.angle) == (b.shot_type.value, b.angle))
    say("   连续两镜完全一样：%d 处" % same)
    say("   机位：%s" % "  ".join("%s %d" % (k, v) for k, v in
                                 collections.Counter((sh.camera_move or "").strip()
                                                     for sh in shots).most_common()))
    say("   主体：%s" % "  ".join("%s %d" % (k or "(空)", v) for k, v in
                                 collections.Counter((sh.subject or "").strip()
                                                     for sh in shots).most_common(6)))
    say("   时长 %.1f~%.1f 秒，平均 %.1f" % (
        min(float(sh.duration or 0) for sh in shots),
        max(float(sh.duration or 0) for sh in shots),
        sum(float(sh.duration or 0) for sh in shots) / len(shots)))
    say("")
OUT.close()
