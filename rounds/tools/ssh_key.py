"""Put our public key on the other machine, so the pipeline can ssh/scp."""
import os
import subprocess
import sys
from pathlib import Path

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

key_dir = Path.home() / ".ssh"
key_dir.mkdir(exist_ok=True)
key = key_dir / "id_ed25519"
pub = key.with_suffix(".pub")

if not key.exists():
    print("生成密钥:", key)
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-C",
                    "dramakit@5080", "-f", str(key)], check=True)
print("公钥:", pub.read_text().strip()[:80], "...")

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)
keydata = pub.read_text()

sftp = cli.open_sftp()
remote_dir = f"/home/{user}/.ssh"
try:
    sftp.stat(remote_dir)
except FileNotFoundError:
    cli.exec_command(f"mkdir -p {remote_dir} && chmod 700 {remote_dir}")
with sftp.open(f"{remote_dir}/authorized_keys", "a") as f:
    f.write(keydata)
cli.exec_command(f"chmod 600 {remote_dir}/authorized_keys")
sftp.close()
print("公钥已装到", remote_dir)

_in, out, err = cli.exec_command("ls -la ~/.ssh/ && wc -l ~/.ssh/authorized_keys")
print(out.read().decode("utf-8", "replace"))
cli.close()
