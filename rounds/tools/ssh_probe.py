"""Look at the other machine: what is on it, and can we get in?

    python rounds/tools/ssh_probe.py 192.168.31.7 david dangyang
"""
import sys

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    cli.connect(host, username=user, password=pw, timeout=20,
                banner_timeout=30, auth_timeout=30)
except Exception as e:  # noqa: BLE001
    print("连不上:", type(e).__name__, str(e)[:200])
    raise SystemExit(1)
print("登录成功:", user, "@", host)

cmds = [
    "uname -a",
    "whoami; id",
    "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader",
    "df -h / /home 2>/dev/null | head -5",
    "python3 --version; which python3 pip3",
    "ls -la ~ | head -30",
    "find / -maxdepth 3 -iname 'ComfyUI*' -o -maxdepth 3 -iname 'comfyui*' 2>/dev/null | head -10",
    "ls -la /home 2>/dev/null | head",
    "free -g | head -3",
    "which git ffmpeg; ffmpeg -version 2>/dev/null | head -1",
]
for c in cmds:
    print(f"\n$ {c}")
    _in, out, err = cli.exec_command(c, timeout=60)
    o = out.read().decode("utf-8", "replace").strip()
    e = err.read().decode("utf-8", "replace").strip()
    if o:
        print(o[:1500])
    if e:
        print("[stderr]", e[:400])
cli.close()
