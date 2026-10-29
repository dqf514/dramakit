"""Can we run ComfyUI on the other machine - and with what?"""
import sys

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)


def run(c, sudo=False):
    if sudo:
        c = f"echo '{pw}' | sudo -S bash -c \"{c}\""
    _in, out, err = cli.exec_command(c, timeout=180)
    return (out.read().decode("utf-8", "replace").strip(),
            err.read().decode("utf-8", "replace").strip())


cmds = [
    ("docker images 2>&1 | head -12", True),
    ("docker ps -a 2>&1 | head -8", True),
    ("ls -la /var/run/docker.sock", False),
    ("tar -tzf /opt/deploy/comfyui/comfyui.tar.gz 2>/dev/null | head -8", False),
    ("tar -tzf /opt/deploy/comfyui/comfyui.tar.gz 2>/dev/null | grep -E 'comfyui_version|main.py|nodes_minimax_h3' | head -10", False),
    ("/data/hfenv/bin/python -c 'import torch,transformers;print(torch.__version__, transformers.__version__, torch.cuda.is_available())' 2>&1 | tail -3", False),
    ("ls /data/hfenv/lib/python*/site-packages 2>/dev/null | head -30", False),
    ("ls -la /data/comfyui/models/../ | head; df -h /data | tail -1", False),
]
for c, s in cmds:
    o, e = run(c, sudo=s)
    print(f"\n$ {'sudo ' if s else ''}{c}")
    if o:
        print(o[:2200])
    if e and "Password:" not in e:
        print("[stderr]", e[:300])
cli.close()
