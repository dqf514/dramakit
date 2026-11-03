"""Whether the two instances are meant to be run as one compose project.

A container that was half-made by hand is easiest to finish by hand, but
if a compose file already declares both, starting it by hand puts the
second one outside the project's control - a later `up` recreates one and
leaves the other, and the two drift.

So the file is read first, along with what the project currently owns.
"""
import subprocess
import sys
from pathlib import Path

SSH = ["ssh", "-i", r"C:\Users\David\.ssh\id_ed25519",
       "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
       "-o", "BatchMode=yes", "david@192.168.31.8"]
out = []


def sh(cmd, timeout=90):
    try:
        r = subprocess.run(SSH + [cmd], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


out.append("=== 找 compose 文件 ===")
out.append(sh("ls -la ~/dramakit/ 2>&1 | head -20"))
out.append(sh("find / -maxdepth 4 -name 'docker-compose*.yml' -o -maxdepth 4 "
              "-name 'docker-compose*.yaml' 2>/dev/null | head -10"))

out.append("")
out.append("=== ~/dramakit/docker-compose.h3.yml ===")
out.append(sh("cat ~/dramakit/docker-compose.h3.yml 2>&1 | head -80"))

out.append("")
out.append("=== compose 项目状态 ===")
out.append(sh("cd ~ && docker compose -p dramakit-h3 config --services 2>&1 | head -10"))
out.append(sh("docker compose -p dramakit-h3 ps -a 2>&1 | head -12"))

out.append("")
out.append("=== 网络 ===")
out.append(sh("docker network ls | grep -i dramakit 2>&1"))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\compose.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
