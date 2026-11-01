"""Why does the console not see the project that is running?

The job is recorded in 星际之光's project.json, but the API answers with
an error for it and the project list does not include it - so the
workbench would have nothing to show even if it looked. This reads the
error and the list, both read-only.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
out = []


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


try:
    d = get("/api/projects")
    out.append("=== /api/projects ===")
    for p in d.get("projects", []):
        out.append("  " + json.dumps(p, ensure_ascii=False)[:220])
except Exception as e:  # noqa: BLE001
    out.append("ERR: " + str(e)[:200])

out.append("")
for name in ("星际之光", "九天灭魔传"):
    q = urllib.parse.quote(name)
    try:
        d = get("/api/projects/" + q)
        out.append(f"=== /api/projects/{name} ===")
        out.append("  " + json.dumps({k: v for k, v in d.items() if k in ("ok", "error")},
                                     ensure_ascii=False)[:300])
    except Exception as e:  # noqa: BLE001
        out.append(f"=== {name} ERR: {str(e)[:150]}")

out.append("")
out.append("=== 磁盘上的项目 ===")
root = Path(r"E:\dramakit\projects")
for d in sorted(root.iterdir()):
    pj = d / "project.json"
    if d.is_dir() and pj.exists():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            ss = data.get("stage_status", {})
            eps = data.get("episodes", [])
            out.append(f"  {d.name}: 集 {len(eps)}  stage {json.dumps(ss, ensure_ascii=False)[:120]}")
        except Exception as e:  # noqa: BLE001
            out.append(f"  {d.name}: project.json 解析失败 {str(e)[:80]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\vis.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
