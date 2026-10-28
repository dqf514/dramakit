"""Turn the mouth-sync on and run it on the finished episode."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.models import Status
from dramakit.project import ProjectStore

# 1) the setting
p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = "  lipsync: false                           # 打开后每个有台词的镜头都会过一遍 MuseTalk"
new = "  lipsync: true                            # 打开后每个有台词的镜头都会过一遍 MuseTalk"
assert old in s, "lipsync 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml: lipsync 打开")

# 2) let the stages that follow run again
name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
proj = store.load()
for ep in proj.episodes:
    for st in ("lipsync", "subtitle", "compose", "qc"):
        ep.stage_status.pop(st, None)
store.save(proj)
print(f"{name}: 阶段已重置")
