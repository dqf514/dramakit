"""What the cast page is handed, and how many pictures it would show.

The character now has one reference image, but the card shows a large one
and a row of thumbnails under it - the same file twice, because the sheet
and the list are built from the same record and the list does not know
that. The picture is also dropped into a portrait box that crops a wide
sheet down to a strip.

So the endpoint is called and the deduplication the page performs is
reproduced here: if it comes out as one, the page with the fix shows one;
if it comes out as two, something is still feeding it twice.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
out = []

proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
slug = json.loads((proj / "project.json").read_text(encoding="utf-8"))["meta"]["name"]
q = urllib.parse.quote(slug)

# find the detail endpoint by trying the ones the page could use
candidates = [f"/api/projects/{q}", f"/api/projects/{q}/detail",
              f"/api/project?slug={q}", f"/api/projects/{q}?detail=1"]
detail = None
for u in candidates:
    try:
        with urllib.request.urlopen(BASE + u, timeout=30) as r:
            d = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        out.append(f"  {u} -> {type(e).__name__}")
        continue
    if isinstance(d, dict) and "ref_sheet_url" in json.dumps(d, ensure_ascii=False):
        detail = d
        out.append(f"  端点 {u} ✓")
        break
    out.append(f"  {u} -> 无角色数据")

if not detail:
    out.append("**没找到返回角色数据的端点**")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\castapi.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit


def find_chars(o):
    if isinstance(o, dict):
        if "ref_sheet_url" in o:
            return [o]
        acc = []
        for v in o.values():
            acc += find_chars(v)
        return acc
    if isinstance(o, list):
        acc = []
        for v in o:
            acc += find_chars(v)
        return acc
    return []


chars = find_chars(detail)
out.append(f"  角色数 {len(chars)}")
out.append("")
for c in chars[:4]:
    sheet = c.get("ref_sheet_url") or ""
    urls = list(c.get("ref_urls") or [])
    merged = [u for u in dict.fromkeys([sheet] + urls) if u]
    out.append(f"  {c.get('name')}:")
    out.append(f"    ref_sheet_url = {sheet}")
    out.append(f"    ref_urls      = {json.dumps(urls, ensure_ascii=False)}")
    out.append(f"    **页面合并去重后 = {len(merged)} 张**")
    if merged:
        out.append(f"      {merged[0]}")

out.append("")
out.append("=== 结论 ===")
counts = {}
for c in chars:
    sheet = c.get("ref_sheet_url") or ""
    urls = list(c.get("ref_urls") or [])
    n = len([u for u in dict.fromkeys([sheet] + urls) if u])
    counts[n] = counts.get(n, 0) + 1
for n, v in sorted(counts.items()):
    out.append(f"  {n} 张: {v} 个角色")
if set(counts) == {1}:
    out.append("  → 全部角色只有 1 张图，reflist 会被隐藏，只显示一张")
else:
    out.append("  → 仍有角色显示多张，需要进一步查")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\castapi.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
