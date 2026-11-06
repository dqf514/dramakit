"""Write the script again, with the editor.

The six episodes are marked done, so the stage would skip them: their
status is put back to pending first, and then only the script stage is
run.  Everything after it is now stale - the shots were cut from the
old lines - and it is said out loud, because a film made from the old
script is a film of the old script.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request

ROOT = pathlib.Path(r"E:\dramakit")
sys.path.insert(0, str(ROOT))

from dramakit.models import Status  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

PROJECT = "穿成亿万总裁他前妻"
BASE = "http://127.0.0.1:8080"


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read())


store = ProjectStore.open(ROOT / "projects" / PROJECT)
proj = store.load()
for ep in proj.episodes:
    ep.stage_status["script"] = Status.PENDING
store.save(proj)
print("  %d 集的编剧状态已重置" % len(proj.episodes))

r = post("/api/run", {"project": PROJECT, "stages": ["script"],
                      "episodes": [], "overrides": {}})
print("  任务:", r.get("job"))
jid = r.get("job")
t0 = time.time()
while time.time() - t0 < 900:
    j = get("/api/jobs?id=" + jid).get("job") or {}
    if j.get("status") in ("done", "error", "interrupted", "cancelled"):
        print("  结果:", j.get("status"), (j.get("error") or "")[:120])
        break
    time.sleep(4)

print()
print("=== 日志 ===")
for l in (get("/api/logs?n=120").get("lines") or []):
    m = l["msg"]
    if "script" in m or "打磨" in m:
        print("  [%s] %s" % (l["lv"], m[:200]))
