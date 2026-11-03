"""Resume, and watch for the two lanes running at the same time.

The change under test is that the render no longer waits for every prompt
in the project: a shot is drawn when that shot is ready. The proof is two
stages marked running at once, and the remote card working while the
writers still are - so this watches both machines and the stage list
together, and reports whether the overlap ever happened.
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


def gpu(host):
    cmd = "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader"
    if host != "local":
        cmd = f"ssh -o ConnectTimeout=6 -o StrictHostKeyChecking=no {host} \"{cmd}\""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout.strip().split("\n")[0].strip() if r.stdout.strip() else "?")


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


out.append("=== 提交恢复 ===")
r0, i0, v0 = state()
out.append(f"  起始 进行中 {r0} 首帧 {i0} 视频 {v0}  "
           f"5080 {gpu('local')}%  3090 {gpu('david@192.168.31.7')}%")
res = post("/api/run", {"project": SLUG, "season": 1,
                        "stages": ["analyze", "character", "segment", "script",
                                   "storyboard", "promptgen", "voice", "visual",
                                   "lipsync", "subtitle", "music", "precheck",
                                   "compose", "qc"]})
out.append("  " + json.dumps(res, ensure_ascii=False)[:140])

overlap = 0
video_seen = False
for i in range(1, 21):
    time.sleep(30)
    running, imgs, vids = state()
    g5, g3 = gpu("local"), gpu("david@192.168.31.7")
    if len(running) > 1:
        overlap += 1
    if vids > 0:
        video_seen = True
    mark = " ←两道并行" if len(running) > 1 else ""
    out.append(f"  +{30*i:>4}秒 5080 {g5:>4}% 3090 {g3:>4}%  "
               f"首帧 {imgs:>3} 视频 {vids:>3}  进行中 {running}{mark}")

out.append("")
out.append(f"两道并行的采样数: {overlap} / 20")
out.append(f"出过视频: {video_seen}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\final.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
