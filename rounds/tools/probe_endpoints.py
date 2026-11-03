"""The new endpoints, called the way a page would call them.

The listing has to answer with an empty list rather than with a lookup of
a key nobody asked for, and the resume has to say what it found before it
starts anything - because a resume that silently begins a fresh run is
worse than one that refuses, since it costs a full pass over the book to
discover it went back to chapter one.
"""
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:8080"
out = []


def get(path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(BASE + path, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def post(path: str, payload: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
slug = json.loads((proj / "project.json").read_text(encoding="utf-8"))["meta"]["name"]
out.append(f"项目 slug = {slug!r}")

out.append("")
out.append("=== GET /api/jobs（不带 id，应为列表）===")
st, body = get("/api/jobs")
out.append(f"  HTTP {st}  {body[:400]}")
try:
    d = json.loads(body)
    out.append(f"  有 'jobs' 键: {'jobs' in d}   值: {d.get('jobs')}")
    out.append(f"  旧的 'job' 键: {'job' in d}")
except Exception as e:  # noqa: BLE001
    out.append(f"  解析失败: {e}")

out.append("")
out.append("=== GET /api/jobs?id=xxx（应为单个）===")
st, body = get("/api/jobs?id=nonexistent")
out.append(f"  HTTP {st}  {body[:300]}")

out.append("")
out.append(f"=== POST /api/resume project={slug} ===")
st, body = post("/api/resume", {"project": slug})
out.append(f"  HTTP {st}  {body[:500]}")

out.append("")
out.append("=== POST /api/resume 不存在的项目 ===")
st, body = post("/api/resume", {"project": "does_not_exist_xyz"})
out.append(f"  HTTP {st}  {body[:300]}")

# what the project says its last run is
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
out.append("")
out.append("=== 项目里的 last_run ===")
out.append(f"  {json.dumps(raw['meta'].get('last_run') or {}, ensure_ascii=False)}")
out.append("  （空 = 还没有断点记录，因为这个中断发生在该机制之前）")

# interrupted stages, which is what a resume would pick up
out.append("")
out.append("=== 中断的阶段（续跑会从这里继续）===")
for k, v in (raw.get("stage_status") or {}).items():
    if v != "done":
        out.append(f"  {k}: {v}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\endpoints.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
