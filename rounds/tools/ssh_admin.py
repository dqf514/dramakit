"""The admin panel's run-mode switch - the API that hands the GPUs over."""
import re
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


o = run("grep -n -E 'app\\.(get|post)|@app|mode|def ' /opt/deploy/admin/app.py | head -60")
print("===== app.py 的接口")
print(o[:3000])

o = run("grep -n -A 30 -E 'def .*mode|运行模式|mode' /opt/deploy/admin/app.py | head -80")
print("\n===== 模式切换的实现")
print(o[:4000])
cli.close()
