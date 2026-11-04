"""What the pipeline made of one chapter of a real book.

The two stages that were wrong are the two that cost the most: the
adaptation and the coverage.  This reads back what the pipeline wrote
and prints it - the scenes, the lines, and the shot list with its
angles - so the result can be read rather than trusted.
"""
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.project import ProjectStore

store = None
for r in sorted(pathlib.Path(r"E:\dramakit\projects").glob("*/project.json")):
    s = ProjectStore.open(r.parent)
    if s.load().meta.name == "分镜验证":
        store = s
        break
if store is None:
    raise SystemExit("找不到工程")

proj = store.load()
for ep in proj.episodes:
    print(f"\n=== 第{ep.index}集《{ep.title}》 {len(ep.scenes)} 场 "
          f"{ep.total_shots} 镜 ===")
    for sc in ep.scenes:
        print(f"\n【{sc.location}·{sc.time_of_day}】{sc.summary}")
        for l in sc.lines:
            print(f"   {l.speaker}（{l.emotion}）: {l.text}")
    print("\n--- 分镜 ---")
    for sc in ep.scenes:
        for sh in sc.shots:
            who = "、".join(sh.characters)
            print(f"  {sh.index:2d}. {sh.shot_type.value:4} {sh.angle:4} "
                  f"{sh.height:3} {sh.lens:3} 主体={sh.subject[:12]:14} "
                  f"线={sh.line_indices} 人={who}")
            print(f"      {sh.action[:100]}")
