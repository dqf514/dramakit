"""Compose the first episode now, without waiting for the other two.

The pipeline's tail - lips, subtitles, the check, the film - runs when
the drawing lane is finished, and the drawing lane is finished when
every shot of every episode has been drawn. The first episode is
complete; the other two are not, and that is eleven hours away.

So the tail is run for the first episode alone, with the run stopped
first: the tail writes the whole project, and a run that is drawing at
the same time would have its own work written over.

Then the run starts again where it was.
"""
import json
import time
import urllib.error
import urllib.request

CONSOLE = "http://127.0.0.1:8080"


def post(path, body, timeout=120):
    req = urllib.request.Request(
        CONSOLE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}


def get(path, timeout=60):
    with urllib.request.urlopen(CONSOLE + path, timeout=timeout) as r:
        return json.loads(r.read())


print("=== 1. 停掉正在跑的流水线 ===")
jobs = get("/api/jobs").get("jobs") or []
for j in jobs:
    if j.get("kind") == "run_pipeline" and j.get("status") in ("running", "queued"):
        print("   停", j.get("id"), post("/api/jobs/stop", {"job": j.get("id")}))
time.sleep(10)

print()
print("=== 2. 只跑第一集的尾巴（对嘴/字幕/预检/合成/质检）===")
jid = None
for i in range(60):
    st, r = post("/api/run", {"project": "星际骷髅兵", "episodes": [1],
                              "stages": ["lipsync", "subtitle", "precheck",
                                         "compose", "qc"]})
    if st == 200:
        print("   提交:", st, json.dumps(r, ensure_ascii=False)[:140])
        jid = r.get("job")
        break
    print(f"   还没停干净（第 {i+1} 次）: {str(r)[:80]}")
    time.sleep(15)
if not jid:
    raise SystemExit(1)

t0 = time.time()
last = ""
while time.time() - t0 < 7200:
    time.sleep(15)
    job = get(f"/api/jobs?id={jid}").get("job") or {}
    status = job.get("status")
    if status != last:
        print(f"   [{time.strftime('%H:%M:%S')}] 状态: {status}")
        last = status
    if status not in ("queued", "running"):
        print("   结果:", json.dumps(job.get("result"), ensure_ascii=False)[:400])
        print("   错误:", str(job.get("error"))[:400])
        break
else:
    print("   超时")
