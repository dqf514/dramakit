"""What is in this tutorial? Title, parts, and where to get them."""
import json
import sys
import urllib.request

BVID = sys.argv[1] if len(sys.argv) > 1 else "BV15NnM6vEYy"

req = urllib.request.Request(
    f"https://api.bilibili.com/x/web-interface/view?bvid={BVID}",
    headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30) as r:
    d = json.load(r)
data = d.get("data") or {}
print("标题:", data.get("title"))
print("UP:", (data.get("owner") or {}).get("name"))
print("时长:", data.get("duration"), "秒")
print("简介:", (data.get("desc") or "")[:600])
print()
print("分集:")
for p in data.get("pages") or []:
    print(f"  p{p['page']:>2}  {p['duration']:>5}s  {p['part']}")
print()

only = [int(x) for x in sys.argv[2:]]
pages = {p["page"]: p for p in data.get("pages") or []}
for page in (only or sorted(pages)):
    p = pages.get(page)
    if not p:
        continue
    url = (f"https://api.bilibili.com/x/player/playurl?bvid={BVID}&cid={p['cid']}"
           f"&qn=32&fnval=1&fourk=0")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://www.bilibili.com/video/{BVID}/?p={page}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    durls = (j.get("data") or {}).get("durl") or []
    if not durls:
        print(f"{page}\t{p['duration']}\t0\t")
        continue
    du = durls[0]
    print(f"{page}\t{p['duration']}\t{du['size']}\t{du['url']}")
