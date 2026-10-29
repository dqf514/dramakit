"""Who is using the GPUs on the other machine, and can we get sudo?"""
import sys

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)


def run(c, use_sudo=False):
    if use_sudo:
        c = f"echo '{pw}' | sudo -S {c}"
    _in, out, err = cli.exec_command(c, timeout=90)
    return (out.read().decode("utf-8", "replace").strip(),
            err.read().decode("utf-8", "replace").strip())


for c in ["nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv",
          "ps aux | grep -E 'vllm|python' | grep -v grep | head -8",
          "systemctl list-units --type=service --state=running 2>/dev/null | head -20",
          "docker ps -a 2>&1 | head -8",
          "ls -la /opt/ComfyUI 2>&1 | head -5",
          "ls /data/hfenv 2>/dev/null; ls /data/vllm 2>/dev/null",
          "ip -4 addr show | grep inet | head -5"]:
    o, e = run(c)
    print(f"\n$ {c}")
    if o:
        print(o[:1800])
    if e:
        print("[stderr]", e[:300])

print("\n=== 试 sudo ===")
o, e = run("id; docker ps -a 2>&1 | head -8", use_sudo=True)
print(o[:1500] if o else "")
if e:
    print("[stderr]", e[:300])
cli.close()
