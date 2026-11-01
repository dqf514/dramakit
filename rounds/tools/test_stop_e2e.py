"""Ask a run to stop from the page, and see it stop.

The whole point of the button is that a plan found to be wrong can be
abandoned without taking the server with it. So: start a real run on the
project that has no work yet, let it begin, press stop, and watch what
the stage is written up as. Stopped, not failed - the run was refused,
not broken.
"""
import json
import time
import urllib.parse
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


def stage():
    d = json.loads((Path(r"E:\dramakit\projects") / SLUG / "project.json")
                   .read_text(encoding="utf-8"))
    return d.get("stage_status", {})


out.append("=== 起一个会跑一阵的任务 ===")
out.append("  之前: " + json.dumps(stage(), ensure_ascii=False))

# ask for a stage that talks to the model and takes a while
r = post("/api/run", {"project": SLUG, "stages": ["analyze"]})
out.append("  /api/run -> " + json.dumps(r, ensure_ascii=False)[:200])
jid = r.get("job")

if jid:
    time.sleep(4)
    out.append("  4 秒后: " + json.dumps(stage(), ensure_ascii=False))
    j = get("/api/jobs?id=" + jid).get("job") or {}
    out.append("  任务状态: " + j.get("status", "?"))

    out.append("")
    out.append("=== 按停止 ===")
    s = post("/api/jobs/stop", {})
    out.append("  /api/jobs/stop -> " + json.dumps(s, ensure_ascii=False)[:200])

    # wait for it to let go
    for _ in range(20):
        time.sleep(3)
        st = stage()
        if not any(v == "running" for v in st.values()):
            break
    out.append("  停下后: " + json.dumps(stage(), ensure_ascii=False))

    j2 = get("/api/jobs?id=" + jid).get("job") or {}
    out.append("  任务状态: " + j2.get("status", "?")
               + ("  错误: " + str(j2.get("error"))[:120] if j2.get("error") else ""))

out.append("")
out.append("=== 服务还在吗 ===")
out.append("  " + json.dumps(get("/api/health"), ensure_ascii=False)[:80])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\stoptest.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
