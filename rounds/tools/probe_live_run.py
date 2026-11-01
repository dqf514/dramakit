"""Is the run working, stuck, or ignoring the stop?

The mechanism raises correctly when tested alone, so the question is what
the live run is actually doing: how many episodes it has finished, whether
that number is still moving, and whether the stop it was handed is the one
the endpoint set.
"""
import json
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
SLUG = "妖怪志"
root = Path(r"E:\dramakit\projects") / SLUG
out = []


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


def scripted():
    d = json.loads((root / "project.json").read_text(encoding="utf-8"))
    n = 0
    for e in d.get("episodes", []):
        if (e.get("stage_status") or {}).get("script") == "done":
            n += 1
    return n, d.get("stage_status", {})


n1, ss1 = scripted()
out.append(f"现在: 已写剧本 {n1} 集, stage_status={json.dumps(ss1, ensure_ascii=False)}")

for i in range(4):
    time.sleep(10)
    n2, ss2 = scripted()
    out.append(f"  +{10*(i+1)} 秒: {n2} 集  {json.dumps(ss2, ensure_ascii=False)}")

out.append("")
out.append("=== 任务注册表 ===")
j = get("/api/jobs")
out.append("  " + json.dumps(j, ensure_ascii=False)[:300])

out.append("")
out.append("=== 这个 job 的进度 ===")
# find any running job
for k in (get("/api/jobs").get("jobs") or []):
    out.append("  " + json.dumps(k, ensure_ascii=False)[:200])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\live.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
