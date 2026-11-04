"""Can this machine hold a GitHub git session open at all?

The push gets as far as sending and then the connection is reset. That
is either the network or the client. This asks the question the same
way git does - the same request, the same address - but without git,
so the two can be told apart.
"""
import socket
import ssl
import sys
import time

HOST = "github.com"
IP = sys.argv[1] if len(sys.argv) > 1 else "172.182.252.133"
PATH = "/dqf514/dramakit.git/info/refs?service=git-upload-pack"

ctx = ssl.create_default_context()
t0 = time.time()
try:
    s = socket.create_connection((IP, 443), timeout=15)
    print(f"  TCP {IP}:443 通 {(time.time()-t0)*1000:.0f}ms")
    with ctx.wrap_socket(s, server_hostname=HOST) as ss:
        print(f"  TLS 成功 {ss.version()}")
        req = (f"GET {PATH} HTTP/1.1\r\nHost: {HOST}\r\n"
               "User-Agent: git/2.49.0\r\nAccept: */*\r\n\r\n")
        ss.sendall(req.encode())
        total = 0
        while True:
            chunk = ss.recv(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > 200000:
                break
        print(f"  收到 {total} 字节，用时 {time.time()-t0:.1f} 秒")
        print("  会话保持住了 ✓" if total > 1000 else "  数据太少 ✗")
except Exception as e:  # noqa: BLE001
    print(f"  失败：{type(e).__name__} {str(e)[:120]}（{time.time()-t0:.1f} 秒）")
