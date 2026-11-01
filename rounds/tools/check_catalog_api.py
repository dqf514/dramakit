"""Does the console know the chapters of a project?"""
import json
import sys
import urllib.request

name = sys.argv[1] if len(sys.argv) > 1 else "魔兽世界"
req = urllib.request.Request(
    "http://127.0.0.1:8080/api/catalog",
    data=json.dumps({"project": name}).encode("utf-8"),
    headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=60) as r:
    d = json.loads(r.read())
print("  ok:", d.get("ok"))
print("  卷:", d.get("volumes"))
chs = d.get("chapters") or []
print("  章节:", len(chs), "个")
for c in chs[:4]:
    print(f"    [{c.get('volume')}] 第{c.get('index')}章 {c.get('title')}  "
          f"{c.get('chars')}字  {c.get('file')}")
