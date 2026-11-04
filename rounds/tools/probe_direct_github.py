"""Can the machine still get to GitHub without the proxy?

The proxy is on, and its fake-IP DNS answers for every name - including
the names of its own servers, which is why the subscription could not
be updated and why every foreign site times out at five seconds.

But the router still answers DNS, and a real address is a real address:
if GitHub's own address still works when it is asked for by name and
reached directly, the push can go that way, with the proxy out of the
way for this one connection.
"""
import socket
import ssl
import struct
import time


def ask_dns(server, name, timeout=6):
    """Ask a DNS server for one address, by hand."""
    qid = b"\x12\x34"
    header = qid + struct.pack(">HHHHH", 1, 0x0100, 1, 0, 0, 0)
    qname = b""
    for part in name.split("."):
        qname += bytes([len(part)]) + part.encode()
    qname += b"\x00"
    packet = header + qname + struct.pack(">HH", 1, 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((server, 53))
        s.send(packet)
        data = s.recv(512)
    finally:
        s.close()
    # the answer's last four bytes are the address
    if len(data) < 16:
        return None
    return ".".join(str(b) for b in data[-4:])


print("=== 用路由器的 DNS 问 github.com ===")
real = None
for server in ("192.168.31.1", "223.5.5.5", "119.29.29.29"):
    try:
        ip = ask_dns(server, "github.com")
        print(f"  {server:16} -> {ip}")
        if ip and not ip.startswith("198.18."):
            real = ip
            break
    except Exception as e:  # noqa: BLE001
        print(f"  {server:16} -> {type(e).__name__}")

if not real:
    print("  拿不到真实地址")
    raise SystemExit(1)

print()
print(f"=== 直连真实地址 {real} ===")
t0 = time.time()
try:
    s = socket.create_connection((real, 443), timeout=12)
    with ssl.create_default_context().wrap_socket(s, server_hostname="github.com") as ss:
        print(f"  TLS 成功 {(time.time()-t0)*1000:.0f}ms  {ss.version()}")
        ss.settimeout(12)
        ss.sendall(("GET /dqf514/dramakit.git/info/refs?service=git-upload-pack "
                    f"HTTP/1.1\r\nHost: github.com\r\n"
                    "User-Agent: git/2.49.0\r\nAccept: */*\r\n"
                    "Connection: close\r\n\r\n").encode())
        total = 0
        while total < 4096:
            chunk = ss.recv(4096)
            if not chunk:
                break
            total += len(chunk)
        print(f"  git 请求收到 {total} 字节")
        print("  ✓ 这条路是通的" if total > 200 else "  ✗ 请求没回来")
except Exception as e:  # noqa: BLE001
    print(f"  {type(e).__name__}: {str(e)[:100]} ({time.time()-t0:.1f}s)")
