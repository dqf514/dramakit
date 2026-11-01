"""When do the chapters load, and does an older import have them?"""
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


print("=== 前端页面：什么时候加载章节 ===")
html = get("/api/health")  # just to be sure the server is the new one
req = urllib.request.Request("http://127.0.0.1:8080/",
                             headers={"Content-Type": "text/html"})
with urllib.request.urlopen(req, timeout=30) as r:
    page = r.read().decode("utf-8", "replace")
print("  打开项目时（renderWorkbench 里）加载:", "loadChapters(slug)" in page)
print("  页面里有章节卡片:", "work-chapters" in page)

print()
print("=== 现有项目有没有章节 ===")
projects = get("/api/projects").get("projects", [])
print(f"  {len(projects)} 个项目")
for p in projects:
    name = p.get("slug") or p.get("name")
    try:
        d = post("/api/catalog", {"project": name})
        chs = d.get("chapters") or []
        print(f"  {name:<18} 卷 {len(d.get('volumes') or [])} 个 | 章 {len(chs)} 个"
              + (f" | 第1章: {chs[0].get('title')}" if chs else "  ← 没有章节数据"))
    except Exception as e:  # noqa: BLE001
        print(f"  {name:<18} 查不到: {str(e)[:60]}")
