"""Resume the run, and watch whether the card comes alive.

Everything it needs is on disk: four episodes of prompts, eleven voice
samples, sixty-three reference pictures. What was missing was the order -
the render waited for every prompt in the project, and it does not have
to. This starts the run again and reports whether the remote card is
working while the writers are still writing.
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
    return r.stdout.strip()


def state():
    d = json.loads((root / "project.json").read_text(encoding="utf-8"))
    eps = d.get("episodes", [])
    imgs = vids = 0
    for e in eps:
        for sc in e.get("scenes", []):
            for sh in sc.get("shots", []):
                imgs += 1 if sh.get("image_path") else 0
                vids += 1 if sh.get("video_path") else 0
    return (d.get("stage_status", {}),
            {"episodes": len(eps), "首帧": imgs, "视频": vids})


out.append("=== 恢复前 ===")
ss, n = state()
out.append(f"  {json.dumps(ss, ensure_ascii=False)}")
out.append(f"  {n}")
out.append(f"  GPU: {gpu()}")

out.append("")
out.append("=== 提交恢复 ===")
r = post("/api/run", {"project": SLUG, "season": 1,
                      "stages": ["analyze", "character", "segment", "script",
                                 "storyboard", "promptgen", "voice", "visual",
                                 "lipsync", "subtitle", "music", "precheck",
                                 "compose", "qc"]})
out.append("  " + json.dumps(r, ensure_ascii=False)[:160])

# watch
for i in range(1, 13):
    time.sleep(20)
    ss, n = state()
    g = gpu()
    out.append(f"  +{20*i:>3} 秒  GPU {g:<22} 首帧 {n['首帧']:>3} 视频 {n['视频']:>3}  "
               f"{json.dumps({k: v.value if hasattr(v, 'value') else v for k, v in ss.items() if 'run' in str(v) or 'ing' in str(v)}, ensure_ascii=False)}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\resume.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
