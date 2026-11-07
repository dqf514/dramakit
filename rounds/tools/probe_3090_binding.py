"""The two ComfyUI workers: which card is each one on?

The cards are asked over ssh, because the answer is in the container's
own settings and in what the driver says is running.
"""
import json
import subprocess

HOST = "192.168.31.8"

CMDS = {
    "每台的显卡": "nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader",
    "跑着的进程": "nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader",
    "容器的卡": "for c in comfyui-h3-a comfyui-h3-b; do echo \"== $c\"; "
                "docker inspect $c --format '{{json .Config.Env}}'; "
                "docker inspect $c --format '{{json .HostConfig.DeviceRequests}}'; done",
    "容器里的卡": "for c in comfyui-h3-a comfyui-h3-b; do echo \"== $c\"; "
                  "docker exec $c printenv CUDA_VISIBLE_DEVICES; "
                  "docker exec $c nvidia-smi --query-gpu=index,memory.used --format=csv,noheader; done",
}


def sh(cmd):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes",
                        HOST, cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    return (r.stdout or "") + (r.stderr or "")


for name, cmd in CMDS.items():
    print("=== %s" % name)
    print(sh(cmd).strip() or "  (没有回答)")
    print()
