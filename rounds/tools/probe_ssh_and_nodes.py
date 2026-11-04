"""Can the machine reach GitHub over SSH, and what are the proxy's servers?

SSH does not go through the system proxy, so it is a separate way out.
If it answers with "publickey" rather than a timeout, the way is open
and all it needs is the key on the account.
"""
import pathlib
import re
import socket
import subprocess
import time

print("=== SSH 到 GitHub ===")
for target, port in (("git@github.com", 22), ("git@ssh.github.com", 443)):
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=20",
           "-o", "BatchMode=yes", "-p", str(port), "-T", target]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                       encoding="utf-8", errors="replace")
    out = ((r.stdout or "") + (r.stderr or "")).strip().split("\n")[0]
    print(f"  {target}:{port}  {time.time()-t0:.1f}s  {out[:120]}")

print()
print("=== 订阅里的服务器 ===")
p = pathlib.Path(
    r"C:\Users\David\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev"
    r"\profiles\R9xqQPSyj9R5.yaml")
text = p.read_text(encoding="utf-8", errors="replace")
hosts = []
for m in re.finditer(r"server:\s*([^\s#]+)", text):
    h = m.group(1).strip("'\"")
    if h and not h.startswith("10.255.") and h not in hosts:
        hosts.append(h)
print(f"  {len(hosts)} 个真实服务器")
for h in hosts[:8]:
    s = socket.socket()
    s.settimeout(8)
    t0 = time.time()
    try:
        s.connect((h, 443))
        print(f"    通   {h} ({(time.time()-t0)*1000:.0f}ms)")
    except Exception as e:  # noqa: BLE001
        print(f"    不通 {h}  {type(e).__name__}")
    finally:
        s.close()
