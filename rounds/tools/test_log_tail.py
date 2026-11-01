"""Do the run's own words reach the page now?

The pipeline logs what it is doing through one logger, and nothing was
reading it - no handler was configured, so INFO was dropped and the log
file stayed empty while a run went. This starts a real stage and reads
the tail back, so the lines shown are the lines the run wrote.
"""
import json
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
SLUG = "九天灭魔传"
out = []


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


def tail(n=40):
    return get(f"/api/logs?n={n}").get("lines", [])


out.append("=== 起一个任务，看日志会不会动 ===")
before = tail(10)
out.append(f"  之前有 {len(before)} 行（接口返回的）")

r = post("/api/run", {"project": SLUG, "chapters": [1, 2], "stages": ["analyze"]})
out.append("  /api/run -> " + json.dumps(r, ensure_ascii=False)[:120])

for i in range(6):
    time.sleep(5)
    lines = tail(6)
    out.append(f"  +{5*(i+1)} 秒: {len(lines)} 行")
    if lines:
        break

out.append("")
out.append("=== 日志内容（最近 25 行）===")
for ln in tail(25):
    ts = time.strftime("%H:%M:%S", time.localtime(ln["t"]))
    out.append(f"  {ts} [{ln['lv']}] {ln['msg'][:150]}")

out.append("")
out.append("=== 停掉 ===")
out.append("  " + json.dumps(post("/api/jobs/stop", {}), ensure_ascii=False)[:140])
time.sleep(4)
out.append("  停后最近 4 行:")
for ln in tail(4):
    ts = time.strftime("%H:%M:%S", time.localtime(ln["t"]))
    out.append(f"    {ts} [{ln['lv']}] {ln['msg'][:130]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\logs.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
