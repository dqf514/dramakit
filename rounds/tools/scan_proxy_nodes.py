"""Which of the subscription's own servers are still there?

The merged configuration the proxy is running has every node pointing
at a placeholder address, which is why every foreign site times out at
exactly five seconds: the proxy is waiting for a server that is not
there. The real addresses are in the subscription profile, so those are
what gets tested.
"""
import pathlib
import re
import socket
import time

PROFILE = pathlib.Path(
    r"C:\Users\David\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev"
    r"\profiles\R9xqQPSyj9R5.yaml")
text = PROFILE.read_text(encoding="utf-8", errors="replace")

servers = {}
for m in re.finditer(r"server:\s*([^\s#]+)", text):
    host = m.group(1).strip('"\'')
    if host and not host.startswith("10.255.") and host not in servers:
        # find the port near it
        tail = text[m.end():m.end() + 200]
        pm = re.search(r"port:\s*(\d+)", tail)
        servers[host] = int(pm.group(1)) if pm else 443

print(f"=== 订阅里的服务器 {len(servers)} 个 ===")
alive = []
for host, port in servers.items():
    s = socket.socket()
    s.settimeout(6)
    t0 = time.time()
    try:
        s.connect((host, port))
        alive.append((host, port, (time.time() - t0) * 1000))
    except Exception:  # noqa: BLE001
        pass
    finally:
        s.close()

if alive:
    print(f"=== 通的有 {len(alive)} 个 ===")
    for host, port, ms in sorted(alive, key=lambda x: x[2]):
        print(f"  {ms:7.0f}ms  {host}:{port}")
else:
    print("一个都不通")
