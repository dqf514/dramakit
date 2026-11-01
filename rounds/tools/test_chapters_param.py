"""Does an instruction's chapters reach the project as chapters?

"前十章" arrives as a range far more often than as ten numbers, so the
range is expanded here. This checks the parser turns it into the chapter
list the run then writes, without running anything.
"""
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.ai import actions

cases = [
    ("前十章", {"chapters": ["1-10"]}),
    ("1到10章", {"chapters": ["1-10"]}),
    ("第3、5、7章", {"chapters": [3, 5, 7]}),
    ("前两集", {"episodes": [1, 2]}),
    ("只要第5集的画面", {"episodes": [5], "stages": ["visual"]}),
]

print("=== 归一化 ===")
for label, raw in cases:
    act = actions._build("run_pipeline", raw, ["测试项目"])
    print(f"  {label:<16} -> chapters={act.params.get('chapters')} "
          f"episodes={act.params.get('episodes')} "
          f"stages={act.params.get('stages')}")

print()
print("=== 确认文案（跑之前显示给用户看的）===")
for raw in ({"chapters": ["1-10"]}, {"chapters": [1, 2, 3]}, {}):
    act = actions._build("run_pipeline", raw, ["测试项目"])
    try:
        msg = actions.describe(act)
    except AttributeError:
        # older name
        msg = str(act)
    print(f"  {raw} -> {msg}")
