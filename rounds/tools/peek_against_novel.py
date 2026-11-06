"""What the script did with the novel.

The novel opens on a hot morning: the workers opening the doors and
windows of the ground floor, the breeze, the laundry, the breakfast
being made.  Then the bedroom, the alarm, the dim light, the
curtain, the crystal lamp, the thick carpet, the balcony, the mirror,
the makeup smeared over a stranger's face.

What came out was a conversation between two people in a bedroom.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(r"E:\dramakit")
sys.path.insert(0, str(ROOT))

from dramakit.project import ProjectStore  # noqa: E402

store = ProjectStore.open(ROOT / "projects" / "穿成亿万总裁他前妻")
proj = store.load()

print("=== 项目里的场景（只有这些是允许用的）===")
for loc in proj.locations:
    print("   %-22s %s" % (loc.name, (loc.description or "")[:70]))

print()
print("=== 每集的场：概要 vs 台词量 ===")
for ep in proj.episodes:
    for sc in ep.scenes:
        lines = len(sc.lines)
        words = sum(len(ln.text) for ln in sc.lines)
        print("  第%s集 %-16s 台词 %2d 句 / %3d 字  | %s"
              % (ep.index, sc.location, lines, words, (sc.summary or "")[:60]))

print()
print("=== 第1集场1 的镜头：几个承载台词 ===")
ep = proj.episodes[0]
sc = ep.scenes[0]
no_talk = 0
for sh in sc.shots:
    has = bool(sh.line_indices)
    if not has:
        no_talk += 1
    print("   %s %s" % ("有台词" if has else "**空镜**", (sh.action or "")[:100]))
print("   → %d/%d 个镜头不承载台词" % (no_talk, len(sc.shots)))
