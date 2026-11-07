"""Is the shot list any good?

The numbers a person can check: every beat filmed, every line carried,
no shot that is the same picture as the one before it, and lengths that
are not all the same.
"""
import pathlib
import re
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore  # noqa: E402

PROJ = r"E:\dramakit\projects\穿成亿万总裁他前妻"
WHICH = int(sys.argv[1]) if len(sys.argv) > 1 else 1

store = ProjectStore.open(PROJ)
proj = store.load()
out = []
for ep in proj.episodes:
    if ep.index != WHICH:
        continue
    out.append("第%d集《%s》 %d 场 %d 镜" % (ep.index, ep.title,
                                            len(ep.scenes), ep.total_shots))
    durs = []
    dup = 0
    covered_beats = set()
    covered_lines = set()
    for sc in ep.scenes:
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
            if prev is not None and (prev.action or "") == (sh.action or ""):
                dup += 1
            prev = sh
            covered_beats |= set(sh.beats or [])
            covered_lines |= set(sh.line_indices or [])
            out.append("      [%s/%s/%s/%s] %s秒  %s"
                       % (sh.shot_type.value, sh.angle, sh.height,
                          sh.camera_move, sh.duration, sh.action))
            out.append("         拍%s 台词%s 角色%s"
                       % (sh.beats, sh.line_indices, sh.characters))
    missing_b = []
    missing_l = []
    for sc in ep.scenes:
        for i in range(1, len(sc.beats) + 1):
            if i not in covered_beats:
                missing_b.append((sc.index, i))
        for i in range(1, len(sc.lines) + 1):
            if i not in covered_lines:
                missing_l.append((sc.index, i))
    out.append("")
    out.append("  镜头 %d 个，时长 %.1f~%.1f 秒（平均 %.1f，%d 种不同长度）"
               % (len(durs), min(durs), max(durs), sum(durs) / len(durs),
                  len(set(durs))))
    out.append("  没拍到的拍点：%s" % (missing_b or "没有"))
    out.append("  没进镜头的台词：%s" % (missing_l or "没有"))
    out.append("  和前一镜一模一样的镜头：%d 个" % dup)

path = pathlib.Path(r"E:\dramakit\rounds\tools\_ep1_report.txt")
path.write_text("\n".join(out), encoding="utf-8")
print("\n".join(out[-4:]))
print("  写到", path)
