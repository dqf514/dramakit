"""Chapters reach the project from the direct endpoint, and a stop lands.

Two things the last patch changed and neither was checked end to end: the
direct /api/run built its own parameter list and dropped chapters, so only
the AI path could limit a book; and the stop's real latency is one model
call, not the next episode. This drives both.
"""
import json
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
SLUG = "九天灭魔传"
root = Path(r"E:\dramakit\projects") / SLUG
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


def meta():
    d = json.loads((root / "project.json").read_text(encoding="utf-8"))
    m = d.get("meta", {})
    return {"chosen": m.get("chosen_chapters") or [],
            "segmented": m.get("segmented_chapters") or [],
            "stages": {k: str(v.value if hasattr(v, "value") else v)
                       for k, v in d.get("stage_status", {}).items()}}


out.append("=== 直连 /api/run 带 chapters ===")
out.append("  之前: " + json.dumps(meta(), ensure_ascii=False))
r = post("/api/run", {"project": SLUG, "chapters": [1, 2, 3],
                      "stages": ["analyze"]})
out.append("  /api/run -> " + json.dumps(r, ensure_ascii=False)[:160])

# the run writes chosen_chapters at its start
for _ in range(12):
    time.sleep(2)
    m = meta()
    if m["chosen"]:
        break
out.append("  落盘后: " + json.dumps(meta(), ensure_ascii=False))

if r.get("job"):
    out.append("")
    out.append("=== 停止，并测延迟 ===")
    time.sleep(4)
    t0 = time.time()
    s = post("/api/jobs/stop", {})
    out.append("  " + json.dumps(s, ensure_ascii=False)[:150])
    for _ in range(60):
        time.sleep(2)
        if meta()["stages"].get("analyze") != "running":
            out.append(f"  落地，用时 {time.time()-t0:.0f} 秒: "
                       + json.dumps(meta()["stages"], ensure_ascii=False))
            break
    else:
        out.append("  120 秒还在跑")

out.append("")
out.append("=== 服务还活着 ===")
out.append("  " + json.dumps(get("/api/health"), ensure_ascii=False)[:80])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\e2e.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
