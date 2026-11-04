"""Push to GitHub through one of the addresses that actually answers.

github.com has several addresses and this network drops some of them
while others work - api, codeload and objects all answer, so the block
is on one address rather than on GitHub. The name is what picks the
wrong one, so the push is told where to go.

The address is not just reachable: it has to carry a whole git request
through, because the one that connects and then resets is no use
either.
"""
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(r"E:\dramakit")
HOST = "github.com"
PATH = "/dqf514/dramakit.git/info/refs?service=git-upload-pack"


def candidates():
    ips = set()
    for dns in ("8.8.8.8", "1.1.1.1", "223.5.5.5", "114.114.114.114",
                "180.76.76.76", "119.29.29.29"):
        try:
            r = subprocess.run(["nslookup", HOST, dns], capture_output=True,
                               text=True, timeout=8)
            for line in r.stdout.split("\n"):
                if "Address" in line and ":" in line:
                    a = line.split(":")[-1].strip()
                    if a and a[0].isdigit():
                        ips.add(a)
        except Exception:  # noqa: BLE001
            pass
    # the ones GitHub is known to answer on
    ips |= {"20.205.243.166", "140.82.112.3", "140.82.113.3",
            "140.82.114.3", "140.82.116.3", "172.182.252.133",
            "20.27.177.113", "20.200.245.247", "20.248.137.48"}
    return sorted(ips)


def carries_a_request(ip, timeout=8):
    """Can this address hold a git request open long enough to answer?"""
    ctx = ssl.create_default_context()
    try:
        s = socket.create_connection((ip, 443), timeout=timeout)
    except Exception:  # noqa: BLE001
        return False
    try:
        with ctx.wrap_socket(s, server_hostname=HOST) as ss:
            ss.settimeout(timeout)
            ss.sendall((f"GET {PATH} HTTP/1.1\r\nHost: {HOST}\r\n"
                        "User-Agent: git/2.49.0\r\nAccept: */*\r\n\r\n").encode())
            total = 0
            while total < 4096:
                chunk = ss.recv(4096)
                if not chunk:
                    break
                total += len(chunk)
            return total > 200
    except Exception:  # noqa: BLE001
        return False
    finally:
        try:
            s.close()
        except Exception:  # noqa: BLE001
            pass


def push(ip):
    cmd = ["git", "-c", "http.sslBackend=schannel",
           "-c", f"http.curloptResolve={HOST}:443:{ip}",
           "push", "origin", "main"]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                       timeout=600, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, "\n".join(l for l in out.split("\n")
                                 if "LF will be replaced" not in l)


def main():
    ips = candidates()
    print(f"=== 试 {len(ips)} 个地址 ===")
    good = []
    for ip in ips:
        ok = carries_a_request(ip)
        print(f"  {ip:18} {'能走完一个 git 请求' if ok else '不行'}")
        if ok:
            good.append(ip)
    if not good:
        print("没有一个地址能走完请求")
        return 1
    for ip in good:
        print(f"\n=== 用 {ip} 推 ===")
        code, out = push(ip)
        print(out.strip()[-600:])
        if code == 0:
            print("\n✓ 推上去了")
            return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
