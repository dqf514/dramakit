import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8080/api/projects", timeout=60) as r:
    ps = json.loads(r.read().decode("utf-8")).get("projects") or []
for p in ps:
    print("  slug:", ascii(p.get("slug")))
    print("  title:", ascii(p.get("title") or p.get("name")))
