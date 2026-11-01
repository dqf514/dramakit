"""Delete every project, one by one, through the console's own API."""
import json
import urllib.request

def post(path, body):
    req = urllib.request.Request(
        "http://127.0.0.1:8080" + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def get(path):
    req = urllib.request.Request("http://127.0.0.1:8080" + path,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


projects = get("/api/projects").get("projects", [])
print(f"现有 {len(projects)} 个项目")
for p in projects:
    name = p.get("slug") or p.get("name")
    r = post("/api/projects/delete", {"project": name})
    ok = r.get("ok") or r.get("error")
    print(f"  {name:<18} {'✓ 移入回收站' if r.get('ok') else '✗ ' + str(r.get('error'))}")

# what is left
after = get("/api/projects").get("projects", [])
print(f"\n删除后还剩 {len(after)} 个")
