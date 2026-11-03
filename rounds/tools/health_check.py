"""The final health check on the running job.

Everything that was fixed has to be seen working at once, not one at a
time: the video going to the card that has the accelerator, the graph
being accepted when a shot has fewer pictures than slots, the two lanes
moving together, and no line of the log showing the fault each fix was
made for.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

CONSOLE = "http://127.0.0.1:8080"
out = []


def get(base, path, timeout=25):
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())

# --- the job -----------------------------------------------------------
jobs = get(CONSOLE, "/api/jobs").get("jobs") or []
run = next((j for j in jobs if j.get("kind") == "run_pipeline"), None)
out.append("=== 任务 ===")
out.append(f"  {run['id'] if run else '无'}  "
           f"status={run['status'] if run else '-'}")

raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
out.append("")
out.append("=== 阶段 ===")
for k, v in (raw.get("stage_status") or {}).items():
    out.append(f"  {k:14} {v}")

# --- the two lanes moving ---------------------------------------------
out.append("")
out.append("=== 两道并行（最近 8 分钟写入）===")
now = time.time()
lanes: dict[str, list] = {}
for f in proj.rglob("*"):
    if not f.is_file():
        continue
    age = now - f.stat().st_mtime
    if age > 480:
        continue
    rel = str(f.relative_to(proj))
    lane = ("写作" if rel.startswith(("audio", "bgm", "episodes"))
            else "绘制" if rel.startswith(("images", "video", "tmp", "characters"))
            else "其他")
    lanes.setdefault(lane, []).append((age, rel))
for lane in ("写作", "绘制"):
    rows = lanes.get(lane) or []
    out.append(f"  {lane}: {len(rows)} 个文件")
    for age, rel in sorted(rows)[:4]:
        out.append(f"      {age:5.0f} 秒前  {rel}")

out.append("")
out.append("=== 产物 ===")
for sub in ("images", "video", "audio", "episodes", "subs"):
    d = proj / sub
    n = len([f for f in d.rglob("*") if f.is_file()]) if d.exists() else 0
    out.append(f"  {sub:10} {n:>4}")

# --- the faults each fix was for --------------------------------------
logs = get(CONSOLE, "/api/logs?lines=400").get("lines") or []
out.append("")
out.append("=== 故障检查（应为空）===")
faults = {
    "房间资产缺失": "没有找到对应的房间资产",
    "空节点被拒": "VALIDATE_INPUTS",
    "类型校验失败": "prompt_outputs_failed_validation",
    "节点类型缺失": "missing_node_type",
}
found = False
for l in logs:
    m = l.get("msg") or ""
    for label, needle in faults.items():
        if needle in m:
            out.append(f"  **{label}**: {m[:150]}")
            found = True
if not found:
    out.append("  （无）")

# --- the accelerator ---------------------------------------------------
out.append("")
out.append("=== SageAttention ===")
i2v = [l for l in logs if "SageAttention" in (l.get("msg") or "")]
out.append(f"  提交记录 {len(i2v)} 条")
for l in i2v[-3:]:
    ts = time.strftime("%H:%M:%S", time.localtime(l.get("t") or 0))
    out.append(f"    {ts} {l.get('msg')}")
no_sage = [l for l in i2v if "无（会慢" in (l.get("msg") or "")]
out.append(f"  无加速的提交: {len(no_sage)}")

# --- errors worth knowing about ---------------------------------------
out.append("")
out.append("=== 最近的 error 级日志 ===")
errs = [l for l in logs if l.get("lv") in ("e", "w")]
for l in errs[-8:]:
    ts = time.strftime("%H:%M:%S", time.localtime(l.get("t") or 0))
    out.append(f"  {ts} [{l.get('lv')}] {(l.get('msg') or '')[:170]}")
if not errs:
    out.append("  （无）")

# --- the card ----------------------------------------------------------
q = get("http://192.168.31.7:8188", "/queue")
out.append("")
out.append("=== 3090 ===")
out.append(f"  队列 运行 {len(q.get('queue_running') or [])} | "
           f"等待 {len(q.get('queue_pending') or [])}")
st = get("http://192.168.31.7:8188", "/system_stats")
dev = (st.get("devices") or [{}])[0]
if dev:
    out.append(f"  VRAM {dev.get('vram_free', 0)/2**30:.1f}GB 空闲 / "
               f"{dev.get('vram_total', 0)/2**30:.1f}GB")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\health.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
