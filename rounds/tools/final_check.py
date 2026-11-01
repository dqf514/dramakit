"""What projects are left, and what a skill actually does at run time."""
import inspect
import json
import sys
import urllib.request

sys.path.insert(0, r"E:\\dramakit")
from dramakit.pipeline import analyze, promptgen, script, storyboard

print("=== 哪些阶段会自动带 skill ===")
for name, mod in (("analyze", analyze), ("script", script),
                  ("storyboard", storyboard), ("promptgen", promptgen)):
    src = inspect.getsource(mod)
    has = ("for_stage" in src) or ("loader" in src)
    print(f"  {name:<11} {'✓ 自动带' if has else '✗ 没有'}")

print()
print("=== 剩下的项目 ===")
req = urllib.request.Request("http://127.0.0.1:8080/api/projects",
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as r:
    d = json.loads(r.read())
for p in d.get("projects", []):
    print(f"  {p['slug']:<14} {p.get('episodes',0)} 集 {p.get('shots',0)} 段 "
          f"{p.get('characters',0)} 角色")
