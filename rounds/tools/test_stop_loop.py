"""Does a looping stage stop at once?

The stop is checked between episodes, which is where a run spends its
hours: 151 episodes is 151 model calls. A stage that makes one long call
- analyze, character - has no such seam and can only stop when the call
returns, and that difference is worth knowing rather than assuming. This
starts the script stage over a hundred and fifty episodes, stops it, and
times how long letting go takes.
"""
import json
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
SLUG = "妖怪志"
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


def stage():
    d = json.loads((Path(r"E:\dramakit\projects") / SLUG / "project.json")
                   .read_text(encoding="utf-8"))
    return d.get("stage_status", {})


out.append("=== 起剧本阶段（151 集）===")
out.append("  之前: " + json.dumps(stage(), ensure_ascii=False))
r = post("/api/run", {"project": SLUG, "stages": ["script"]})
jid = r.get("job")
out.append("  job: " + str(jid))

time.sleep(5)
out.append("  5 秒后: " + json.dumps(stage(), ensure_ascii=False))

out.append("")
out.append("=== 停止，并计时 ===")
t0 = time.time()
s = post("/api/jobs/stop", {})
out.append("  " + json.dumps(s, ensure_ascii=False)[:160])

landed = None
for _ in range(40):
    time.sleep(1)
    st = stage()
    if st.get("script") != "running":
        landed = time.time() - t0
        out.append(f"  停下了，用时 {landed:.1f} 秒: "
                   + json.dumps(st, ensure_ascii=False))
        break
if landed is None:
    out.append("  60 秒还在跑: " + json.dumps(stage(), ensure_ascii=False))

j = get("/api/jobs?id=" + str(jid)).get("job") or {}
out.append("  任务状态: " + str(j.get("status")))

out.append("")
out.append("=== 磁盘上有没有白写的东西 ===")
src = Path(r"E:\dramakit\projects") / SLUG
logs = sorted(src.glob("**/*.log"))
for f in logs[:4]:
    out.append(f"  {f.relative_to(src)}  {f.stat().st_size} B")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\stoploop.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
