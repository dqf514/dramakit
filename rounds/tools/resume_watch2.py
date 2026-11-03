"""Resume, and watch the two lanes run at the same time.

Everything the render needs exists already: four episodes of prompts,
eleven voice samples, the reference pictures. What was missing was the
order - it waited for every prompt in the project. The proof that the
change worked is not that the run resumed but that two stages are running
at once, and that the remote card is working while the writers still are.
"""
import json
import subprocess
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
SLUG = "魔兽世界"
root = Path(r"E:\dramakit\projects") / SLUG
out = []


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def gpu():
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=no",
         "david@192.168.31.7",
         "nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"],
        capture_output=True, text=True)
    return (r.stdout.strip() or "?").split(",")[0].strip()


def state():
    d = json.loads((root / "project.json").read_text(encoding="utf-8"))
    ss = d.get("stage_status", {})
    running = [k for k, v in ss.items()
               if str(v.value if hasattr(v, "value") else v) == "running"]
    imgs = vids = 0
    for e in d.get("episodes", []):
        for sc in e.get("scenes", []):
            for sh in sc.get("shots", []):
                imgs += 1 if sh.get("image_path") else 0
                vids += 1 if sh.get("video_path") else 0
    return running, imgs, vids


out.append("=== 恢复前 ===")
r0, i0, v0 = state()
out.append(f"  进行中 {r0}  首帧 {i0} 视频 {v0}  GPU {gpu()}%")

out.append("")
out.append("=== 提交（整条流水线，季 1）===")
res = post("/api/run", {"project": SLUG, "season": 1,
                        "stages": ["analyze", "character", "segment", "script",
                                   "storyboard", "promptgen", "voice", "visual",
                                   "lipsync", "subtitle", "music", "precheck",
                                   "compose", "qc"]})
out.append("  " + json.dumps(res, ensure_ascii=False)[:150])

max_parallel = 0
for i in range(1, 31):
    time.sleep(20)
    running, imgs, vids = state()
    g = gpu()
    max_parallel = max(max_parallel, len(running))
    flag = "  ← 两道同时在跑" if len(running) > 1 else ""
    out.append(f"  +{20*i:>4} 秒  GPU {g:>4}%  首帧 {imgs:>3} 视频 {vids:>3}  "
               f"进行中 {running}{flag}")

out.append("")
out.append(f"同时进行的阶段最多: {max_parallel}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\resume2.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
