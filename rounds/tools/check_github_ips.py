"""Which of GitHub's addresses can this machine actually reach?

The name resolves to several addresses and only some of them answer.
Git picks the first one it is given and waits twenty seconds for a
reply that never comes, so the push fails while a plain socket to the
same name succeeds - it just happened to pick a different address.
"""
import socket
import time


def all_addresses(host):
    out = []
    try:
        for info in socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM):
            ip = info[4][0]
            if ip not in out:
                out.append(ip)
    except Exception as e:  # noqa: BLE001
        print("  解析失败:", e)
    return out


host = "github.com"
ips = all_addresses(host)
print(f"{host} 解析到: {ips}")
print()
good = []
for ip in ips:
    s = socket.socket()
    s.settimeout(8)
    t0 = time.time()
    try:
        s.connect((ip, 443))
        ms = (time.time() - t0) * 1000
        print(f"  {ip:18} 通  {ms:.0f}ms")
        good.append(ip)
    except Exception as e:  # noqa: BLE001
        print(f"  {ip:18} {type(e).__name__}")
    finally:
        s.close()

print()
if good:
    print("可用的地址:", good)
    print("给 git 用： git -c http.curloptResolve=github.com:443:%s push" % good[0])
else:
    print("一个都连不上")
