"""Which node is the proxy using, and can that node be reached?

Every foreign site times out at exactly five seconds while the local
one answers, so the proxy is up and the way out is not. This reads the
configuration the proxy is actually running - the selected node, and
where that node lives - and tries to reach it.
"""
import re
import socket
import pathlib
import sys

CONF = pathlib.Path(
    r"C:\Users\David\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\clash-verge.yaml")

text = CONF.read_text(encoding="utf-8", errors="replace")
lines = text.split("\n")

print("=== 当前选的节点 ===")
mode = re.search(r"^mode:\s*(\S+)", text, re.M)
print("  模式:", mode.group(1) if mode else "?")
sel = re.search(r"^  proxy:\s*(\S+)", text, re.M)
print("  选中的:", sel.group(1) if sel else "?")

# the proxies block: name -> server/port
proxies = {}
in_block = False
for ln in lines:
    if re.match(r"^proxies:\s*$", ln):
        in_block = True
        continue
    if in_block:
        if ln and not ln.startswith(" ") and not ln.startswith("-"):
            break
        m = re.match(r"^  - name:\s*(.+)$", ln)
        if m:
            name = m.group(1).strip().strip('"\'')
            proxies[name] = {}
            continue
        m = re.match(r"^    server:\s*(\S+)", ln)
        if m and proxies:
            proxies[list(proxies)[-1]]["server"] = m.group(1).strip('"\'')
        m = re.match(r"^    port:\s*(\d+)", ln)
        if m and proxies:
            proxies[list(proxies)[-1]]["port"] = int(m.group(1))

picked = sel.group(1).strip('"\'') if sel else ""
info = proxies.get(picked)
print("  节点信息:", info or "（配置里没找到这个名字）")

if info and info.get("server"):
    host, port = info["server"], info.get("port") or 443
    for host in (host,):
        s = socket.socket()
        s.settimeout(8)
        t0 = __import__("time").time()
        try:
            s.connect((host, port))
            print(f"  出站服务器 {host}:{port} 通 "
                  f"({(__import__('time').time()-t0)*1000:.0f}ms)")
        except Exception as e:  # noqa: BLE001
            print(f"  出站服务器 {host}:{port} {type(e).__name__} "
                  f"({__import__('time').time()-t0:.1f}s)")
        finally:
            s.close()

print()
print("=== 节点数量 ===", len(proxies))
print("=== 前 8 个节点 ===")
for name, d in list(proxies.items())[:8]:
    print(f"  {name[:44]:46} {d.get('server')}:{d.get('port')}")
