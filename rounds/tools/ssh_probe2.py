"""What is the ComfyUI on the other machine like?"""
import sys

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)

cmds = [
    "df -h | head -12",
    "ls -la /data/ 2>/dev/null",
    "ls -la /data/comfyui/ 2>/dev/null | head -25",
    "ls -la /opt/deploy/comfyui/ 2>/dev/null | head -25",
    "ls /data/comfyui/models 2>/dev/null",
    "du -sh /data/comfyui/models/* 2>/dev/null | sort -h | tail -12",
    "find /data/comfyui /opt/deploy/comfyui -maxdepth 2 -name 'main.py' 2>/dev/null",
    "ls /data/comfyui/venv/bin 2>/dev/null | head -8; ls /opt/deploy/comfyui/venv/bin 2>/dev/null | head -8",
    "ls /data/comfyui/custom_nodes 2>/dev/null; ls /opt/deploy/comfyui/custom_nodes 2>/dev/null",
    "ps aux | grep -i comfy | grep -v grep | head -5",
    "which ffmpeg ffprobe; ls /usr/local/bin | head -20",
    "nvidia-smi --query-gpu=index,memory.used --format=csv,noheader",
]
for c in cmds:
    print(f"\n$ {c}")
    _in, out, err = cli.exec_command(c, timeout=90)
    o = out.read().decode("utf-8", "replace").strip()
    e = err.read().decode("utf-8", "replace").strip()
    if o:
        print(o[:2000])
    if e:
        print("[stderr]", e[:300])
cli.close()
