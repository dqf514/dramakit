"""Print the whole prompt H3 gets for one shot."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
idx = int(sys.argv[2]) if len(sys.argv) > 2 else 1
p = ProjectStore(Path(r"E:\\dramakit\\projects") / name).load()
sh = p.episodes[0].scenes[0].shots[idx]
print("镜头:", sh.id, sh.shot_type.value, "台词:", sh.line_indices)
print("动作:", (sh.action or "")[:200])
print("-" * 70)
print(sh.video_prompt or "(没有提示词)")
