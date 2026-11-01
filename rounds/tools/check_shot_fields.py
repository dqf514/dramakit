"""Has the prompt stage written anything, or is it stuck?

288 shots, half an hour, and the probe counted none of them as having a
prompt - which is either a field named differently or a stage that has
produced nothing. The shot's own keys decide which.
"""
import json
import time
from pathlib import Path

root = Path(r"E:\dramakit\projects\魔兽世界")
d = json.loads((root / "project.json").read_text(encoding="utf-8"))

out = []
eps = d.get("episodes") or []
out.append(f"集数 {len(eps)}")

# collect every shot, and tally which fields are ever filled
tally: dict[str, int] = {}
filled: dict[str, int] = {}
shots = []
for e in eps:
    for sc in e.get("scenes", []):
        for sh in sc.get("shots", []):
            shots.append(sh)
            for k, v in sh.items():
                tally[k] = tally.get(k, 0) + 1
                if v not in (None, "", [], {}, -1, False):
                    filled[k] = filled.get(k, 0) + 1

out.append(f"镜头 {len(shots)}")
out.append("")
out.append("=== 镜头字段（非空计数 / 总数）===")
for k in sorted(tally, key=lambda x: -filled.get(x, 0)):
    out.append(f"  {k:<26} {filled.get(k, 0):>4} / {tally[k]}")

out.append("")
if shots:
    out.append("=== 第一个镜头的完整内容 ===")
    out.append(json.dumps(shots[0], ensure_ascii=False, indent=2)[:900])

# per-episode promptgen state
out.append("")
out.append("=== 每集的阶段状态 ===")
for e in eps[:12]:
    out.append(f"  第{e.get('index')}集 {json.dumps(e.get('stage_status', {}), ensure_ascii=False)}")

# recent writes: is the stage producing anything at all?
out.append("")
out.append("=== project.json 最近写入 ===")
pj = root / "project.json"
out.append(f"  {time.strftime('%H:%M:%S', time.localtime(pj.stat().st_mtime))}  "
           f"{pj.stat().st_size // 1024} KB   现在 {time.strftime('%H:%M:%S')}")

# the log, if the tail is up now
try:
    import urllib.request
    with urllib.request.urlopen("http://127.0.0.1:8080/api/logs?n=40", timeout=10) as r:
        lines = json.loads(r.read()).get("lines", [])
    out.append("")
    out.append(f"=== 日志 {len(lines)} 行 ===")
    for ln in lines:
        ts = time.strftime("%H:%M:%S", time.localtime(ln["t"]))
        out.append(f"  {ts} [{ln['lv']}] {ln['msg'][:170]}")
except Exception as e:  # noqa: BLE001
    out.append(f"日志接口: {type(e).__name__} {e}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\shotfields.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
