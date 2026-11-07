import json
import urllib.request


def get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


base = "http://127.0.0.1:8080"
d = get(base + "/api/skills")
print("  selection keys:", list(d["selection"].keys()))
for s in d["skills"]:
    if s["family"] == "genre":
        print("  genre 卡:", s["name"], "|", s["family_zh"], "|", s["title_zh"])
        break
h = get(base + "/api/health")
print("  health:", {k: h.get(k) for k in list(h)[:8]})
n = get(base + "/api/nodes")
print("  节点:", [(x.get("name"), x.get("base_url"), x.get("enabled")) for x in n.get("nodes", [])])
