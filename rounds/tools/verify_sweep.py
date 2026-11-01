"""Did the restart settle what the dead process left running?

The script stage was killed mid-run and stayed marked running, which would
have had the console spinning over work nobody was doing for ever. The
sweep runs at startup; this reads the project to see what it said.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

out = []

# on disk
d = json.loads(Path(r"E:\dramakit\projects\妖怪志\project.json").read_text(encoding="utf-8"))
out.append("=== 磁盘上（重启后）===")
out.append(f"  stage_status: {json.dumps(d.get('stage_status', {}), ensure_ascii=False)}")
out.append(f"  episodes: {len(d.get('episodes') or [])}")

# through the console, the way the page reads it
def get(path):
    with urllib.request.urlopen("http://127.0.0.1:8080" + path, timeout=30) as r:
        return json.loads(r.read())


listed = get("/api/projects").get("projects", [])
out.append("")
out.append("=== 接口 ===")
for p in listed:
    slug = p.get("slug")
    q = urllib.parse.quote(slug, safe="")
    try:
        detail = get("/api/projects/" + q)
        out.append(f"  {slug}: {json.dumps(detail.get('stage_status', {}), ensure_ascii=False)}")
    except Exception as e:  # noqa: BLE001
        out.append(f"  {slug}: ERR {str(e)[:80]}")

out.append("")
try:
    j = get("/api/jobs")
    out.append(f"  /api/jobs: {json.dumps(j, ensure_ascii=False)[:200]}")
except Exception as e:  # noqa: BLE001
    out.append(f"  /api/jobs: {str(e)[:100]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\sweep.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
