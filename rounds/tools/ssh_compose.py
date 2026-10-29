"""Read the deployment: compose file and the notes."""
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
    return out.read().decode("utf-8", "replace").strip()


for c in ["cat /opt/deploy/docker-compose.yml",
          "sed -n '1,80p' /opt/deploy/README.md"]:
    o = run(c)
    print(f"\n===== {c}")
    print(o[:4000])
cli.close()
