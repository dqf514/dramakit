"""Dig into the other machine's ComfyUI setup."""
import sys

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)

cmds = [
    "ls -la /data/comfyui/models/diffusion_models/",
    "ls -la /data/comfyui/models/text_encoders/ /data/comfyui/models/vae/ /data/comfyui/models/loras/",
    "cat /opt/deploy/comfyui/Dockerfile",
    "docker ps -a 2>/dev/null | head -12; docker images 2>/dev/null | head -12",
    "ls -la /opt/deploy/comfyui/h3-api-examples/ | head -20",
    "head -60 /opt/deploy/comfyui/build-h3-workflows.py",
    "head -40 /opt/deploy/comfyui/ui2api.py",
    "nvidia-smi | head -25",
    "sudo -n true 2>/dev/null && echo 'sudo 免密可用' || echo 'sudo 要密码'",
]
for c in cmds:
    print(f"\n$ {c}")
    _in, out, err = cli.exec_command(c, timeout=90)
    o = out.read().decode("utf-8", "replace").strip()
    e = err.read().decode("utf-8", "replace").strip()
    if o:
        print(o[:2500])
    if e:
        print("[stderr]", e[:300])
cli.close()
