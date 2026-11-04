"""Which of the proxy's own servers answer?

The proxy's control surface is the named pipe, and the nodes it is
running can be read out of the configuration it loaded.  If none of
them answer, the proxy is up and the way out is not - and every
foreign site times out at exactly five seconds, which is the proxy
waiting for a server that is not there.
"""
import pathlib
import re
import socket
import time

CONF = pathlib.Path(
    r"C:\Users\David\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev"
    r"\clash-verge.yaml")

text = CONF.read_text(encoding="utf-8", errors="replace")

nodes = []
name = None
for line in text.split("\n"):
    m = re.match(r"^- name:\s*(.+)$", line)
    if m:
        name = m.group(1).strip().strip("\"'")
        continue
    m = re.match(r"^\s+server:\s*(\S+)$", line)
    if m:
        host = m.group(1).strip("\"'")
        nodes.append({"name": name or host, "server": host, "port": 443})
    m = re.match(r"^\s+port:\s*(\d+)$", line)
    if m and nodes:
        nodes[-1]["port"] = int(m.group(1))

real = [n for n in nodes if not n["server"].startswith("10.255.")]
print(f"配置里 {len(nodes)} 个节点，其中 {len(real)} 个有真实服务器")

alive = []
for n in real:
    s = socket.socket()
    s.settimeout(6)
    t0 = time.time()
    try:
        s.connect((n["server"], n["port"]))
        alive.append((n, (time.time() - t0) * 1000))
    except Exception:  # noqa: BLE001
        pass
    finally:
        s.close()

if alive:
    print(f"\n活的 {len(alive)} 个：")
    for n, ms in sorted(alive, key=lambda x: x[1])[:12]:
        print(f"  {ms:7.0f}ms  {n['name'][:40]:42} {n['server']}:{n['port']}")
else:
    print("\n一个都不通 —— 代理没有能用的出口")
