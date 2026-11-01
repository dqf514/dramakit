"""Does the slug the console lists match the directory on disk?

open_store joins the slug onto the projects root and asks for
project.json, which is as simple as it looks - so if it answers "no such
project" for a project the list just handed out, the two names differ
somewhere. This compares them byte for byte rather than by eye, since the
console's own output mangles Chinese.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
ROOT = Path(r"E:\dramakit\projects")
out = []


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


listed = get("/api/projects").get("projects", [])
dirs = {d.name: (d / "project.json").exists() for d in ROOT.iterdir() if d.is_dir()}

out.append("=== 接口列出的 slug（按码位）===")
for p in listed:
    slug = p.get("slug", "")
    out.append(f"  {slug!r}")
    out.append(f"    码位: {[hex(ord(c)) for c in slug]}")
    out.append(f"    在磁盘上有同名目录: {slug in dirs}")
    out.append(f"    该目录有 project.json: {dirs.get(slug)}")

out.append("")
out.append("=== 磁盘目录名（按码位）===")
for name, has_json in dirs.items():
    if has_json:
        out.append(f"  {name!r}")
        out.append(f"    码位: {[hex(ord(c)) for c in name]}")

out.append("")
out.append("=== 用列表里的 slug 原样请求 ===")
for p in listed:
    slug = p.get("slug", "")
    q = urllib.parse.quote(slug, safe="")
    try:
        d = get("/api/projects/" + q)
        out.append(f"  {slug!r} -> ok={d.get('ok')} error={d.get('error')}")
    except Exception as e:  # noqa: BLE001
        out.append(f"  {slug!r} -> HTTP {str(e)[:120]}")

out.append("")
out.append("=== open_store 的判定（直接在磁盘上复现）===")
for p in listed:
    slug = p.get("slug", "")
    root = ROOT / slug
    out.append(f"  {slug!r}: root={root} exists={root.exists()} "
               f"json={(root / 'project.json').exists()}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\slug.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
