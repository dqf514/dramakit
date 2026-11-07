import json
import urllib.request

base = "http://127.0.0.1:8760"
body = json.dumps({"nodes": [{"name": "probe-x", "base_url": "http://127.0.0.1:8188",
                               "roles": "i2v"}]}).encode()
req = urllib.request.Request(base + "/api/nodes/save", data=body,
                              headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        print("  status:", r.status, "len:", len(raw))
        print("  body:", raw[:200])
        print("  headers:", dict(r.headers))
except urllib.error.HTTPError as e:
    print("  HTTP", e.code, e.read()[:300].decode("utf-8", "replace"))
