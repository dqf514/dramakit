"""How much work is the prompt stage actually doing?

It has run half an hour and the sheets trickling out suggest image work,
but the stage only writes text - two model calls per shot. The sheets are
made when a character is first met, so their timing tracks the stage's
progress rather than its cost. This counts the shots and the calls, so the
wait is arithmetic instead of a feeling.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

store = ProjectStore.open(Path(r"E:\dramakit\projects\魔兽世界"))
ctx = Context(Config.load(Config.discover()), store)

eps = ctx.target_episodes()
shots = sum(len(s.shots) for e in eps for s in e.scenes)
scenes = sum(len(e.scenes) for e in eps)
lines = sum(sum(1 for _ in sc.lines) for e in eps for sc in e.scenes)

out = [f"项目: 魔兽世界"]
out.append(f"  参与集数   : {len(eps)}")
out.append(f"  场景       : {scenes}")
out.append(f"  镜头       : {shots}")
out.append(f"  台词行     : {lines}")
out.append("")

cfg = Config.load(Config.discover())
conc = int(cfg.llm.concurrency or 1)
out.append("=== 提示词阶段的调用量 ===")
out.append(f"  并发 workers : {conc}")
out.append(f"  每镜 2 条提示词（出图 + 视频）→ {shots * 2} 次 LLM 调用")
out.append(f"  模型         : {cfg.llm.model}")
out.append("")

# what has actually been written for promptgen
d = json.loads((Path(r"E:\dramakit\projects\魔兽世界") / "project.json")
               .read_text(encoding="utf-8"))
done = 0
total_shots = 0
for e in d.get("episodes", []):
    for sc in e.get("scenes", []):
        for sh in sc.get("shots", []):
            total_shots += 1
            ss = sh.get("status", "")
            if str(ss).endswith("done") or sh.get("prompt"):
                done += 1
out.append("=== 已写提示词的镜头 ===")
out.append(f"  {done} / {total_shots}")
if total_shots:
    pct = done * 100 / total_shots
    out.append(f"  进度 {pct:.0f}%")
    import time
    started = 21 * 3600 + 38 * 60 + 57
    now = time.localtime().tm_hour * 3600 + time.localtime().tm_min * 60 + time.localtime().tm_sec
    elapsed = now - started
    if done:
        rate = elapsed / done
        remain = rate * (total_shots - done)
        out.append(f"  已跑 {elapsed // 60} 分钟，{rate:.0f} 秒/镜")
        out.append(f"  还剩约 {remain // 60} 分钟（{total_shots - done} 镜）")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\pgwork.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
