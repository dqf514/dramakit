"""What does the console already know about a running job?

The workbench shows no progress while a stage runs, so before adding
anything the data has to be found. Two endpoints already exist - the
project detail, which carries the stage statuses, and /api/progress,
which counts what a stage has finished - and both are read here for the
project that is actually running, without disturbing it.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
SLUG = "星际之光"
out = []


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


q = urllib.parse.quote(SLUG)

try:
    d = get("/api/progress?project=" + q)
    out.append("=== /api/progress ===")
    out.append(json.dumps(d, ensure_ascii=False, indent=2)[:1500])
except Exception as e:  # noqa: BLE001
    out.append("progress ERR: " + str(e)[:200])

out.append("")
try:
    d = get("/api/projects/" + q)
    out.append("=== /api/projects/<slug> ===")
    out.append("顶层键: " + str(list(d.keys())))
    out.append("stage_status: " + json.dumps(d.get("stage_status", {}), ensure_ascii=False))
    out.append("meta 阶段: " + json.dumps((d.get("meta") or {}).get("stage_status", {}), ensure_ascii=False))
    out.append("episodes: " + str(len(d.get("episodes") or [])))
    for k in ("jobs", "job", "running", "current_job"):
        if k in d:
            out.append(f"{k}: " + json.dumps(d[k], ensure_ascii=False)[:300])
    out.append("")
    out.append("=== 每集的阶段状态 ===")
    for e in (d.get("episodes") or [])[:8]:
        out.append(f"  第{e.get('index')}集 status={e.get('status')} "
                   f"stage_status={json.dumps(e.get('stage_status', {}), ensure_ascii=False)[:160]}")
except Exception as e:  # noqa: BLE001
    out.append("project ERR: " + str(e)[:200])

out.append("")
try:
    j = get("/api/jobs")
    out.append("=== /api/jobs（无 id）===")
    out.append(json.dumps(j, ensure_ascii=False)[:400])
except Exception as e:  # noqa: BLE001
    out.append("jobs ERR: " + str(e)[:200])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\pg.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
