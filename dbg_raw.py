import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore

proj = Path(r"E:\dramakit\projects") / "轮次02_02"
store = ProjectStore(proj)
p = store.load()
ep = p.episodes[0]

print("=== 项目里的台词 ===")
for si, sc in enumerate(ep.scenes):
    print(f"-- 场景 {si} {sc.location}")
    for l in sc.lines:
        print(f"   {l.id} {l.kind.value:9s} {l.speaker[:8]:8s} dur={l.duration:6.2f} "
              f"emo={l.emotion[:4]:4s} 「{l.text[:22]}」")

ass = next(proj.rglob("ep_001.ass"))
print("\n=== ASS 原文（前 22 行 Dialogue） ===")
n = 0
for line in ass.read_text(encoding="utf-8").splitlines():
    if line.startswith("Dialogue:"):
        print("  ", line[:110])
        n += 1
        if n >= 22:
            break
