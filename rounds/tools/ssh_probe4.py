"""How do we start ComfyUI on the other machine?"""
import sys

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)

cmds = [
    "docker ps -a 2>&1 | head -10",
    "docker images 2>&1 | head -10",
    "which docker; groups",
    "sudo -n -l 2>&1 | head -10",
    "ls -la /data/comfyui/user/default/workflows/H3/ 2>/dev/null | head -20",
    "cat /data/comfyui/download.log 2>/dev/null | tail -20",
    "ls /data/models/ /data/admin/ 2>/dev/null",
    "cat /opt/deploy/comfyui/h3-api-examples/api_minimax_h3_r2v.json",
    "ls -la /data/comfyui/input /data/comfyui/output 2>/dev/null | head -12",
    "systemctl list-units --type=service 2>/dev/null | grep -i -E 'comfy|vllm' | head",
    "ls /etc/systemd/system/ 2>/dev/null | head -20",
]
for c in cmds:
    print(f"\n$ {c}")
    _in, out, err = cli.exec_command(c, timeout=90)
    o = out.read().decode("utf-8", "replace").strip()
    e = err.read().decode("utf-8", "replace").strip()
    if o:
        print(o[:3000])
    if e:
        print("[stderr]", e[:400])
cli.close()
