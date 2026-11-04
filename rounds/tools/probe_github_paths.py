"""Where exactly is the way to GitHub blocked?

The handshakes sometimes go through and the requests never come back.
That is a strange shape for a block, so this asks the three hosts
separately, with the same request, to see which of them answers.
"""
import socket
import ssl
import time

HOSTS = [
    ("github.com", "/"),
    ("github.com", "/dqf514/dramakit.git/info/refs?service=git-upload-pack"),
    ("api.github.com", "/"),
    ("codeload.github.com", "/"),
    ("objects.githubusercontent.com", "/"),
    ("ssh.github.com", "/"),
]


def one(host, path):
    ctx = ssl.create_default_context()
    t0 = time.time()
    try:
        s = socket.create_connection((host, 443), timeout=10)
    except Exception as e:  # noqa: BLE001
        return f"连不上 {type(e).__name__} ({time.time()-t0:.1f}s)"
    try:
        with ctx.wrap_socket(s, server_hostname=host) as ss:
            ss.settimeout(10)
            ss.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
                        "User-Agent: probe/1.0\r\nAccept: */*\r\n"
                        "Connection: close\r\n\r\n").encode())
            total = 0
            first = b""
            while total < 4096:
                chunk = ss.recv(4096)
                if not chunk:
                    break
                if not first:
                    first = chunk[:60]
                total += len(chunk)
            head = first.decode("utf-8", "replace").split("\r\n")[0][:40]
            return (f"{total:>6} 字节  {time.time()-t0:5.1f}s  {head}")
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__} ({time.time()-t0:.1f}s)"
    finally:
        try:
            s.close()
        except Exception:  # noqa: BLE001
            pass


for host, path in HOSTS:
    label = f"{host}{path if len(path) < 30 else '/…git-info'}"
    print(f"  {label:42} {one(host, path)}")
