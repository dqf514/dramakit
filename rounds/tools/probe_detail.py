"""What the workbench can show while a stage runs.

The endpoints work; the page showed nothing because it looked only at
per-episode stage statuses, and ingest/analyze/character belong to the
project and not to any episode. This reads a project detail the way the
page would, so the panel can be built against the real shape.
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
    q = urllib.parse.quote(slug, safe="")
    d = get("/api/projects/" + q)
    out.append("=== 项目 " + slug + " ===")
    out.append("顶层键: " + str(list(d.keys())))
    out.append("stage_status: " + json.dumps(d.get("stage_status", {}), ensure_ascii=False))
    out.append("episodes: " + str(len(d.get("episodes") or [])))
    out.append("characters: " + str(len(d.get("characters") or [])))
    meta = d.get("meta") or {}
    out.append("meta.chapters: " + str(len(meta.get("chapters") or [])))
    out.append("meta.seasons: " + json.dumps(meta.get("seasons", []) if isinstance(meta.get("seasons"), list) else "(无)", ensure_ascii=False)[:200])
    out.append("")
    out.append("=== 每集阶段状态 ===")
    for e in (d.get("episodes") or [])[:8]:
        out.append(f"  第{e.get('index')}集 status={e.get('status')} "
                   f"stage={json.dumps(e.get('stage_status', {}), ensure_ascii=False)[:200]}")
    out.append("")
    try:
        pr = get("/api/progress?project=" + q)
        out.append("=== /api/progress ===")
        out.append(json.dumps(pr, ensure_ascii=False, indent=2)[:900])
    except Exception as e:  # noqa: BLE001
        out.append("progress ERR: " + str(e)[:150])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\detail.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
