"""The direct links for the parts of the tutorial we want to study."""
import json
import sys
import urllib.request

BVID = "BV15Hap6uEvY"

req = urllib.request.Request(
    f"https://api.bilibili.com/x/web-interface/view?bvid={BVID}",
    headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30) as r:
    d = json.load(r)
pages = {p["page"]: p for p in d["data"]["pages"]}

for page in sys.argv[1:]:
    pid = int(page)
    p = pages.get(pid)
    if not p:
        print(f"没有第{pid}集")
        continue
    cid = p["cid"]
    url = (f"https://api.bilibili.com/x/player/playurl?bvid={BVID}&cid={cid}"
           f"&qn=32&fnval=1&fourk=0")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://www.bilibili.com/video/{BVID}/?p={pid}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    if j.get("code") != 0:
        print(f"第{pid}集 失败: {j.get('message')}")
        continue
    durls = j["data"].get("durl") or []
    if not durls:
        print(f"第{pid}集 没有下载地址")
        continue
    du = durls[0]
    print(f"{pid}\t{p['duration']}\t{du['size']}\t{du['url']}")
