"""What the episode looks like.

The scenes, the beats, the lines, and the shots - with the numbers a
person can check: every beat filmed, every line carried, no two shots
that are the same picture.
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
WHICH = int(sys.argv[1]) if len(sys.argv) > 1 else 1
SHOTS = len(sys.argv) > 2 and sys.argv[2] == "shots"

out = []
for ep in proj.episodes:
    if ep.index != WHICH:
        continue
    out.append("第%d集《%s》 %d 场 %d 镜" % (ep.index, ep.title,
                                            len(ep.scenes), ep.total_shots))
    out.append("  %s" % (ep.logline or ""))
    out.append("  钩子：%s" % (ep.hook or ""))
    durs = []
    covered_b, covered_l = set(), set()
    for sc in ep.scenes:
        out.append("")
        out.append("  【%s·%s】%s（%s）" % (sc.location, sc.time_of_day,
                                           sc.summary, sc.mood))
        out.append("    拍点 %d 个：" % len(sc.beats))
        for i, b in enumerate(sc.beats, 1):
            out.append("      %d. %s" % (i, b.action))
        out.append("    台词 %d 句：" % len(sc.lines))
        for i, l in enumerate(sc.lines, 1):
            out.append("      %d. %s（%s）: %s" % (i, l.speaker, l.emotion, l.text))
        out.append("    镜头 %d 个：" % len(sc.shots))
        prev = None
        for sh in sc.shots:
            durs.append(float(sh.duration or 0))
            covered_b |= set(sh.beats or [])
            covered_l |= set(sh.line_indices or [])
            if not SHOTS:
                out.append("      [%s/%s/%s] %s秒  拍%s 台词%s"
                           % (sh.shot_type.value, sh.angle, sh.camera_move,
                              sh.duration, sh.beats, sh.line_indices))
            else:
                out.append("      [%s/%s/%s/%s] %s秒  %s"
                           % (sh.shot_type.value, sh.angle, sh.height,
                              sh.camera_move, sh.duration, sh.action))
                out.append("         角色%s" % sh.characters)
            prev = sh
    miss_b = [(sc.index, i) for sc in ep.scenes
              for i in range(1, len(sc.beats) + 1) if i not in covered_b]
    miss_l = [(sc.index, i) for sc in ep.scenes
              for i in range(1, len(sc.lines) + 1) if i not in covered_l]
    out.append("")
    out.append("  时长 %.1f~%.1f 秒（平均 %.1f，%d 种不同长度）"
               % (min(durs), max(durs), sum(durs) / len(durs), len(set(durs))))
    out.append("  没拍到的拍点：%s" % (miss_b or "没有"))
    out.append("  没进镜头的台词：%s" % (miss_l or "没有"))

text = "\n".join(out)
path = pathlib.Path(r"E:\dramakit\rounds\tools\_ep_report.txt")
path.write_text(text, encoding="utf-8")
print("  %d 行 → %s" % (len(out), path))
