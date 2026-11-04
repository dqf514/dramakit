"""Ask the proxy which node it is using, and whether it can be changed.

The proxy's control interface is a named pipe rather than a port, so
this talks HTTP over the pipe. The question it answers is the one that
matters: which node is selected, and is it one of the placeholders.
"""
import json
import re
import pathlib
import time

CONF = pathlib.Path(
    r"C:\Users\David\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\clash-verge.yaml")
text = CONF.read_text(encoding="utf-8", errors="replace")
m = re.search(r"^external-controller-pipe:\s*'?([^'\r\n]+)'?", text, re.M)
pipe = m.group(1).strip() if m else None
secret = re.search(r"^secret:\s*(\S+)", text, re.M)
print("管道:", pipe)
print("密钥:", (secret.group(1) if secret else "(没有)"))


def ask(path, method="GET", body=None):
    if not pipe:
        return None
    try:
        f = open(pipe, "r+b", buffering=0)
    except Exception as e:  # noqa: BLE001
        print("  打不开管道:", type(e).__name__, e)
        return None
    try:
        payload = b""
        if body is not None:
            payload = json.dumps(body).encode()
        req = (f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n"
               f"Content-Length: {len(payload)}\r\n\r\n").encode() + payload
        f.write(req)
        f.flush()
        time.sleep(1.0)
        data = b""
        for _ in range(30):
            try:
                chunk = f.read(65536)
            except Exception:  # noqa: BLE001
                break
            if not chunk:
                break
            data += chunk
            if b"\r\n\r\n" in data and len(data) > 200:
                break
        head, _, rest = data.partition(b"\r\n\r\n")
        length = 0
        lm = re.search(rb"Content-Length:\s*(\d+)", head, re.I)
        if lm:
            length = int(lm.group(1))
        while len(rest) < length:
            try:
                chunk = f.read(65536)
            except Exception:  # noqa: BLE001
                break
            if not chunk:
                break
            rest += chunk
        return rest.decode("utf-8", "replace")
    finally:
        try:
            f.close()
        except Exception:  # noqa: BLE001
            pass


out = ask("/proxies")
if not out:
    print("  接口没答上")
    raise SystemExit(0)

try:
    d = json.loads(out)
except Exception as e:  # noqa: BLE001
    print("  答的不是 json:", out[:200])
    raise SystemExit(0)

proxies = d.get("proxies") or {}
groups = {k: v for k, v in proxies.items() if v.get("all")}
print()
print("=== 代理组和当前选中 ===")
for name, g in list(groups.items())[:8]:
    now = g.get("now")
    print(f"  组 {name[:26]:28} 选中: {now}")
    # is the selected node a placeholder?
    node = proxies.get(now) or {}
    srv = node.get("server")
    if srv:
        print(f"      它的服务器: {srv}:{node.get('port')}")

print()
print("=== 第一个组里真实可用的节点（前 10 个）===")
for name, g in list(groups.items())[:1]:
    for n in (g.get("all") or [])[:12]:
        node = proxies.get(n) or {}
        srv = node.get("server")
        flag = "" if srv and not srv.startswith("10.255.") else "  <- 占位"
        print(f"  {n[:44]:46} {srv or '-'}{flag}")
