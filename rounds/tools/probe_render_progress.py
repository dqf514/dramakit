"""How far along is the render?

The card writes the clip when it is done, so the output folder says
whether it is working or stuck.
"""
import subprocess

HOST = "192.168.31.8"
CMDS = [
    "docker exec comfyui-h3-b ls -la --time-style=+%H:%M:%S /data/comfyui/output/video 2>/dev/null | tail -6",
    "docker exec comfyui-h3-b sh -c 'ls -la /data/comfyui/output/ 2>/dev/null | head -12'",
    "docker exec comfyui-h3-b nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader",
    "date '+现在 %H:%M:%S'",
]


def sh(cmd):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes",
                        HOST, cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=40)
    return (r.stdout or "").strip() or (r.stderr or "").strip()


for c in CMDS:
    print("=== %s" % c[:60])
    print(sh(c) or "  (没有回答)")
    print()
