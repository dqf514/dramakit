"""Let the pipeline drive the other machine without a password.

Two things were in the way: the docker socket is only for the docker
group, and the compose file reads a .env that only root can read. The
docker group is root-equivalent anyway, so both are opened to it.
"""
import sys

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)


def run(c, timeout=120):
    c = f"echo '{pw}' | sudo -S bash -c \"{c}\""
    _in, out, err = cli.exec_command(c, timeout=timeout)
    return (out.read().decode("utf-8", "replace").strip(),
            err.read().decode("utf-8", "replace").strip())


for c in [
    f"usermod -aG docker {user}",
    "chgrp docker /opt/deploy/.env && chmod 640 /opt/deploy/.env",
    f"id {user}",
    "ls -la /opt/deploy/.env",
]:
    o, e = run(c)
    print(f"$ {c}\n{o or e}")

# the new group needs a new login
print("\n重新登录后验证 docker 免密:")
cli.close()

import subprocess
r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-i",
                    f"C:\\Users\\David\\.ssh\\id_ed25519", f"{user}@{host}",
                    "id; docker ps --format '{{.Names}} {{.Status}}' | head -6"],
                   capture_output=True, text=True, errors="replace")
print(r.stdout.strip()[:800] or r.stderr.strip()[:400])
