"""Where the stills machine is, and what the casting stage is doing.

The remote card was at zero percent because it renders video and the
stage that is running draws pictures on the local one - watching the
wrong machine for the wrong work. This watches both, and counts what the
casting stage has actually produced, since it has been running ten
minutes over two characters.
"""
import json
import subprocess
import time
from pathlib import Path

root = Path(r"E:\dramakit\projects\魔兽世界")
out = []


def gpu(host, port=None):
    cmd = ("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader")
    if host != "local":
        cmd = f"ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no {host} \"{cmd}\""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout.strip().split("\n")[0] if r.stdout.strip() else "?")


def comfy(port):
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/queue", timeout=6) as r:
            q = json.loads(r.read())
        return f"running={len(q.get('queue_running', []))} pending={len(q.get('queue_pending', []))}"
    except Exception as e:  # noqa: BLE001
        return f"读不到({type(e).__name__})"


def stage():
    d = json.loads((root / "project.json").read_text(encoding="utf-8"))
    ss = d.get("stage_status", {})
    return [k for k, v in ss.items()
            if str(v.value if hasattr(v, "value") else v) == "running"]


def images():
    n = 0
    cdir = root / "characters"
    if cdir.exists():
        n = len([f for f in cdir.rglob("*")
                 if f.suffix.lower() in (".png", ".jpg") and "s2" not in str(f)])
    return n


out.append("=== 两台机器 ===")
out.append(f"  本机 5080 (出图)  {gpu('local')}")
out.append(f"  3090  (出视频)    {gpu('david@192.168.31.7')}")
out.append(f"  本机 ComfyUI 队列  {comfy(8188)}")
out.append(f"  3090 ComfyUI 队列  {comfy('x') if False else ''}")

out.append("")
out.append("=== 每 30 秒看一次，共 8 次 ===")
n0 = images()
out.append(f"  起始参考图 {n0} 张，进行中 {stage()}")
for i in range(8):
    time.sleep(30)
    out.append(f"  +{30*(i+1):>4} 秒  本机5080 {gpu('local'):<18} "
               f"3090 {gpu('david@192.168.31.7'):<18} "
               f"参考图 {images():>3}  进行中 {stage()}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\gpus.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
