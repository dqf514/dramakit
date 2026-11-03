"""Check the resumed run is doing both halves, and using the accelerator.

The plan calls for the writers and the drawers to run at the same time,
and for the video to go to the card that has SageAttention. A run that
only draws is half as fast as it should be, and a run that renders without
the accelerator costs a third more on every clip - neither is visible from
a job that simply says "running".

So three things are read: whether both lanes have files moving, whether a
video has reached the card, and what the log said when it was submitted.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8188"          # the card
CONSOLE = "http://127.0.0.1:8080"
out = []


def get(base: str, path: str, timeout: int = 25):
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())

# --- the console: job, stages, log ------------------------------------
jobs = get(CONSOLE, "/api/jobs").get("jobs") or []
run = next((j for j in jobs if j.get("kind") == "run_pipeline"
            and j.get("status") == "running"), None)
out.append("=== 运行中的流水线任务 ===")
if run:
    out.append(f"  {run['id']}  status={run['status']}  "
               f"progress={json.dumps(run.get('progress') or {}, ensure_ascii=False)[:300]}")
else:
    out.append("  **没有运行中的任务**")

raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
out.append("")
out.append("=== 阶段状态 ===")
for k, v in (raw.get("stage_status") or {}).items():
    out.append(f"  {k:14} {v}")

# --- the two lanes: are files moving in both? -------------------------
out.append("")
out.append("=== 两道并行的证据（最近 6 分钟内的写入）===")
now = time.time()
buckets: dict[str, list] = {}
for f in proj.rglob("*"):
    if not f.is_file():
        continue
    age = now - f.stat().st_mtime
    if age > 360:
        continue
    rel = str(f.relative_to(proj))
    lane = ("写作" if rel.startswith(("audio", "bgm", "episodes"))
            else "绘制" if rel.startswith(("images", "video", "tmp/refs", "tmp/handoff", "characters"))
            else "其他")
    buckets.setdefault(lane, []).append((age, rel))
for lane in ("写作", "绘制", "其他"):
    rows = buckets.get(lane) or []
    out.append(f"  {lane}: {len(rows)} 个文件")
    for age, rel in sorted(rows)[:5]:
        out.append(f"      {age:5.0f} 秒前  {rel}")

out.append("")
out.append("=== 产物计数 ===")
for sub in ("images", "video", "audio", "episodes", "subs"):
    p = proj / sub
    n = len([f for f in p.rglob("*") if f.is_file()]) if p.exists() else 0
    out.append(f"  {sub:10} {n:>4}")

# --- the card: is it busy, and on what -------------------------------
q = get(BASE, "/queue")
out.append("")
out.append("=== 3090 队列 ===")
if "error" in q:
    out.append(f"  读不到: {q['error']}")
else:
    running = q.get("queue_running") or []
    pending = q.get("queue_pending") or []
    out.append(f"  运行中 {len(running)} | 等待 {len(pending)}")
    for item in running[:2]:
        try:
            prompt = item[2] if isinstance(item, list) else {}
            out.append(f"      节点数 {len(prompt)}  "
                       f"有 SageAttention: "
                       f"{'PathchSageAttentionKJ' in json.dumps(prompt)}")
        except Exception:  # noqa: BLE001
            pass

# --- what the console logged when it submitted ------------------------
logs = get(CONSOLE, "/api/logs?lines=120").get("lines") or []
out.append("")
out.append("=== 控制台日志（含 SageAttention / i2v / 错误）===")
hits = [l for l in logs if any(k in (l.get("msg") or "")
                               for k in ("SageAttention", "i2v", "visual",
                                         "promptgen", "失败", "error",
                                         "渲染节点池", "自动选用"))]
for l in hits[-25:]:
    ts = time.strftime("%H:%M:%S", time.localtime(l.get("t") or 0))
    out.append(f"  {ts} [{l.get('lv')}] {(l.get('msg') or '')[:190]}")
if not hits:
    out.append(f"  （{len(logs)} 行里没有匹配，最后 8 行：）")
    for l in logs[-8:]:
        ts = time.strftime("%H:%M:%S", time.localtime(l.get("t") or 0))
        out.append(f"  {ts} [{l.get('lv')}] {(l.get('msg') or '')[:190]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\lanes.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
