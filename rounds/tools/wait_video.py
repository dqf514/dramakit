"""Wait for one clip to land, so the whole cycle is seen once.

Every part of it has been checked separately: the workflow validates, the
card accepts, the render finishes. What has not been seen is the clip
arriving in the project with the right shape, which is the only step the
rest of the pipeline can use - a render the console never picks up is
indistinguishable from one that never ran.

So the project's video folder is watched, and when a file appears its
real duration, size, resolution and sound track are read.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

out = []
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
vdir = proj / "video"
before = {f.name for f in vdir.glob("*.mp4")}
out.append(f"开始时 video/ 有 {len(before)} 个")
t0 = time.time()
TIMEOUT = 1500

new = None
while time.time() - t0 < TIMEOUT:
    now = {f.name for f in vdir.glob("*.mp4")}
    added = now - before
    if added:
        new = sorted(added)[0]
        break
    time.sleep(20)

if new:
    p = vdir / new
    out.append("")
    out.append(f"=== 新视频落盘 +{time.time()-t0:.0f}s ===")
    out.append(f"  {new}  {p.stat().st_size/1024:.0f} KB")
    out.append(f"  时间 {time.strftime('%H:%M:%S')}")
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,r_frame_rate,"
             "duration,nb_frames,channels", "-of", "json", str(p)],
            capture_output=True, text=True, timeout=60)
        info = json.loads(r.stdout or "{}")
        for s in info.get("streams", []):
            out.append("  " + json.dumps(s, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        out.append(f"  ffprobe: {e}")
else:
    out.append(f"")
    out.append(f"**{TIMEOUT} 秒内没有新视频**")

# --- the state around it ----------------------------------------------
with urllib.request.urlopen("http://192.168.31.7:8188/queue", timeout=25) as r:
    q = json.loads(r.read())
out.append("")
out.append(f"3090 队列: 运行 {len(q.get('queue_running') or [])} | "
           f"等待 {len(q.get('queue_pending') or [])}")

with urllib.request.urlopen("http://127.0.0.1:8080/api/logs?lines=60",
                            timeout=25) as r:
    logs = json.loads(r.read()).get("lines") or []
out.append("")
out.append("=== 最近 i2v / 出视频 日志 ===")
for l in logs:
    m = l.get("msg") or ""
    if any(k in m for k in ("i2v", "出视频", "完成", "失败", "error")):
        ts = time.strftime("%H:%M:%S", time.localtime(l.get("t") or 0))
        out.append(f"  {ts} [{l.get('lv')}] {m[:190]}")

out.append("")
out.append("=== 产物计数 ===")
for sub in ("images", "video", "audio", "episodes", "subs"):
    d = proj / sub
    n = len([f for f in d.rglob("*") if f.is_file()]) if d.exists() else 0
    out.append(f"  {sub:10} {n:>4}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\landed.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
