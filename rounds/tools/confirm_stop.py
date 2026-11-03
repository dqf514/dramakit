"""Did the stop land, and what survived it?

The plan was submitted, the button was pressed, and the question is what
the project says now: which stage gave up, and how many episodes had been
written to disk before it did.
"""
import json
import time
from pathlib import Path

pj = Path(r"E:\dramakit\projects\魔兽世界\project.json")
for i in range(30):
    time.sleep(3)
    d = json.loads(pj.read_text(encoding="utf-8"))
    ss = d.get("stage_status", {})
    if ss.get("promptgen") != "running":
        break

d = json.loads(pj.read_text(encoding="utf-8"))
ss = d.get("stage_status", {})
eps = d.get("episodes", [])
done = [e.get("index") for e in eps
        if (e.get("stage_status") or {}).get("promptgen") in ("done",)]

out = [
    f"停止后 promptgen = {ss.get('promptgen')}",
    f"promptgen 完成的集: {done} / {len(eps)}",
    "全部阶段: " + json.dumps(ss, ensure_ascii=False),
    "",
    "每集的阶段状态:",
]
for e in eps:
    out.append(f"  第{e.get('index')}集 {json.dumps(e.get('stage_status', {}), ensure_ascii=False)}")

out.append("")
out.append("=== 磁盘上还剩什么 ===")
root = Path(r"E:\dramakit\projects\魔兽世界")
src = root / "source"
out.append(f"  ep_*.txt  {len(list(src.glob('ep_*.txt')))} 个")
out.append(f"  volumes/  {len(list((src / 'volumes').glob('*.txt')))} 个")
cdir = root / "characters"
if cdir.exists():
    out.append(f"  角色参考图 {len([f for f in cdir.rglob('*') if f.suffix.lower() in ('.png', '.jpg')])} 张")
shots_total = shots_prompt = 0
for e in eps:
    for sc in e.get("scenes", []):
        for sh in sc.get("shots", []):
            shots_total += 1
            if sh.get("prompt"):
                shots_prompt += 1
out.append(f"  镜头 {shots_total}，已有出图提示词 {shots_prompt}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\stopped.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
