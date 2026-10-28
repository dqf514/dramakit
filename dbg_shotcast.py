import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1]
p = ProjectStore(Path(r"E:\dramakit\projects") / name).load()
ep = p.episodes[0]
for sc in ep.scenes:
    print("=== 场景", sc.index, sc.location)
    for sh in sc.shots:
        act = (sh.action or "")[:34]
        print(f"   {sh.id} {sh.shot_type.value:<6} {str(sh.characters):<26} "
              f"lines={sh.line_indices} 「{act}」")
    for l in sc.lines:
        if l.kind.value == "dialogue":
            print(f"      台词 {l.speaker:<8} 「{l.text[:18]}」")
