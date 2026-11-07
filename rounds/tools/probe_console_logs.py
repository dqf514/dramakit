import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8080/api/logs?n=400", timeout=20) as r:
    d = json.loads(r.read().decode("utf-8"))
lines = d.get("lines") or []
print("  日志 %d 行" % len(lines))
for l in lines[-8:]:
    print("   ", str(l)[:190])
hits = [l for l in lines if "script" in str(l).lower()
        or "分镜" in str(l) or "storyboard" in str(l).lower()]
for l in hits[-25:]:
    print("   ", str(l)[:190])
