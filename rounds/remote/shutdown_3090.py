"""Shut the 3090 machine down cleanly."""
import sys
import time

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)


def run(c, timeout=120):
    _in, out, err = cli.exec_command(c, timeout=timeout)
    return (out.read().decode("utf-8", "replace").strip(),
            err.read().decode("utf-8", "replace").strip())


# 1) stop the workers so nothing is half written
o, e = run("docker compose -p dramakit-h3 -f /home/david/dramakit/"
           "docker-compose.h3.yml down 2>&1 | tail -5")
print("停下 H3 工作进程:")
print(o or e)

# 2) the machine goes down
print("关机...")
run("echo '%s' | sudo -S shutdown -h now" % pw, timeout=20)

# 3) wait until it stops answering
for i in range(12):
    time.sleep(10)
    try:
        cli2 = paramiko.SSHClient()
        cli2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cli2.connect(host, username=user, password=pw, timeout=8,
                     banner_timeout=8)
        cli2.close()
        print(f"  [{i*10:>4}s] 还能连上")
    except Exception:  # noqa: BLE001
        print(f"  [{i*10:>4}s] 已经关机")
        break
cli.close()
