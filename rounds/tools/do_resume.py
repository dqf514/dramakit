"""Resume the run, and watch that it actually starts.

A resume that accepts the plan and then does nothing looks exactly like a
resume that works, until the first file fails to appear. So the call is
followed by a wait and a second look: the job has to be running, and the
project's stages have to move out of interrupted and into running.
"""
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:8080"
out = []


def get(path: str):
    try:
        with urllib.request.urlopen(BASE + path, timeout=25) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except Exception as e:  # noqa: BLE001
        return 0, {"error": f"{type(e).__name__}: {e}"}


def post(path: str, payload: dict):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except Exception as e:  # noqa: BLE001
        return 0, {"error": f"{type(e).__name__}: {e}"}


proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
slug = json.loads((proj / "project.json").read_text(encoding="utf-8"))["meta"]["name"]

# --- nothing else running ---------------------------------------------
st, body = get("/api/jobs")
running = [j for j in (body.get("jobs") or []) if j.get("status") == "running"]
out.append(f"启动前运行中的任务: {len(running)}")
for j in running:
    out.append(f"  {j['id']} {j['kind']}")

if running:
    out.append("已有任务在跑，不再启动")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\resume.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

# --- start it ----------------------------------------------------------
out.append("")
out.append("=== POST /api/resume ===")
st, body = post("/api/resume", {"project": slug})
out.append(f"  HTTP {st}  {json.dumps(body, ensure_ascii=False)[:400]}")
jid = body.get("job") or ""
if not jid:
    out.append("  **没有启动**")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\resume.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

# --- watch it for a while ---------------------------------------------
out.append("")
out.append(f"=== 跟踪任务 {jid} ===")
t0 = time.time()
last = None
for i in range(24):          # up to ~2 minutes
    time.sleep(5)
    st, body = get(f"/api/jobs?id={jid}")
    job = body.get("job") or {}
    status = job.get("status")
    prog = job.get("progress") or {}
    sig = (status, json.dumps(prog, sort_keys=True, ensure_ascii=False))
    if sig != last:
        last = sig
        out.append(f"  +{time.time()-t0:5.0f}s  status={status} "
                   f"progress={json.dumps(prog, ensure_ascii=False)[:220]}")
    if status != "running":
        out.append(f"  结束: {json.dumps(job, ensure_ascii=False)[:600]}")
        break

# --- what the project now says ----------------------------------------
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
out.append("")
out.append("=== 项目阶段状态 ===")
for k, v in (raw.get("stage_status") or {}).items():
    out.append(f"  {k:14} {v}")
out.append(f"  last_run.stages = {(raw['meta'].get('last_run') or {}).get('stages')}")

out.append("")
out.append("=== 最近被写的文件 ===")
now = time.time()
files = [(now - f.stat().st_mtime, f) for f in proj.rglob("*") if f.is_file()]
files = [(a, f) for a, f in files if a < 300]
for a, f in sorted(files)[:12]:
    out.append(f"  {a:5.0f} 秒前  {f.relative_to(proj)}")
if not files:
    out.append("  （5 分钟内无写入）")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\resume.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
