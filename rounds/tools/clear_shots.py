"""Clear the shots of the given episodes so the director can do them again."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
eps = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [1]

store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
proj = store.load()
n = 0
for ep in proj.episodes:
    if ep.index not in eps:
        continue
    for sc in ep.scenes:
        n += len(sc.shots)
        sc.shots = []
        sc.status = None
        sc._shot_budget = None
    ep.stage_status.pop("storyboard", None)
    ep.stage_status.pop("promptgen", None)
    ep.stage_status.pop("visual", None)
store.save(proj)
print(f"{name}: 清掉 {n} 个旧镜头（第 {eps} 集）")
for ep in proj.episodes:
    if ep.index in eps:
        print(f"  第{ep.index}集 目标时长 {ep.duration_target}s")
