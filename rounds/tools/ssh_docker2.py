"""Why did the ComfyUI container die, and how is it deployed?"""
import sys

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)


def run(c):
    c = f"echo '{pw}' | sudo -S bash -c \"{c}\""
    _in, out, err = cli.exec_command(c, timeout=120)
    return (out.read().decode("utf-8", "replace").strip(),
            err.read().decode("utf-8", "replace").strip())


cmds = [
    "docker logs comfyui --tail 30 2>&1 | tail -30",
    "ls -la /opt/deploy/ | head -20",
    "find /opt/deploy -maxdepth 2 -name '*.sh' -o -maxdepth 2 -name 'docker-compose*' -o -maxdepth 2 -name '*.yml' 2>/dev/null | head -20",
    "grep -rl 'gpu-memory-utilization' /opt/deploy /data/admin 2>/dev/null | head -5",
    "docker logs vllm-qwen38 --tail 5 2>&1 | tail -5",
    "cat /sys/fs/cgroup/memory.max 2>/dev/null; free -m | head -2",
]
for c in cmds:
    o, e = run(c)
    print(f"\n$ {c}")
    if o:
        print(o[:2500])
    if e and "Password:" not in e:
        print("[stderr]", e[:300])
cli.close()
