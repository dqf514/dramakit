import collections
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore

store = ProjectStore(Path(r"E:\dramakit\projects\测试短剧"))
proj = store.load()

c = collections.Counter()
for ep in proj.episodes:
    for sc in ep.scenes:
        for l in sc.lines:
            c[l.emotion] += 1
print("全剧情绪分布:", dict(c))
print()
for ep in proj.episodes:
    for sc in ep.scenes:
        for l in sc.lines:
            sp = l.speaker or "旁白"
            print(f"  {sp:6s} [{l.emotion:4s}] {l.text[:36]}")
