"""Does the console hand the page a scene's reference pictures?

The cast page renders thumbnails from ref_urls, and the viewer needs the
same list to page through. This asks the API what a location actually
carries, so the wiring is built against the real shape rather than the
one the code suggests.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


out = []
listed = get("/api/projects").get("projects", [])
slug = next((p["slug"] for p in listed), None)
if not slug:
    out.append("没有项目")
else:
    d = get("/api/projects/" + urllib.parse.quote(slug, safe=""))
    locs = d.get("locations") or []
    out.append(f"项目 {slug}: {len(locs)} 个场景")
    for l in locs[:6]:
        out.append(f"  {l.get('name')!r}")
        out.append(f"    键: {sorted(l.keys())}")
        out.append(f"    ref_urls: {json.dumps(l.get('ref_urls'), ensure_ascii=False)[:220]}")
        out.append(f"    ref_images: {json.dumps(l.get('ref_images'), ensure_ascii=False)[:220]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\locs.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
