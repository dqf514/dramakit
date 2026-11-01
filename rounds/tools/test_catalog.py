"""Does the cut find the chapters and the volumes?"""
import json
import urllib.parse
import urllib.request

novel = ("卷一 少年\n\n" +
         "".join(f"第{i}章 初醒\n\n苏晚睁开眼睛，发现自己回到了婚礼现场。" * 3 + "\n"
                 for i in range(1, 4)) +
         "\n卷二 崛起\n\n" +
         "".join(f"第{i}章 崛起\n\n周砚川坐在轮椅上看着她走进来。" * 3 + "\n"
                 for i in range(4, 7)))

body = json.dumps({"name": "分卷测试", "text": novel}).encode("utf-8")
req = urllib.request.Request(
    "http://127.0.0.1:8080/api/upload", data=body,
    headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=300) as r:
    d = json.loads(r.read())
print("ok:", d.get("ok"), "| 项目:", d.get("project"), "| 字数:", d.get("chars"))
cat = d.get("catalog") or {}
print("切分:", cat)

# the table of contents, by POST
slug = d.get("project") or ""
if slug:
    req2 = urllib.request.Request(
        "http://127.0.0.1:8080/api/catalog",
        data=json.dumps({"project": slug}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req2, timeout=60) as r2:
        toc = json.loads(r2.read())
    print("卷:", toc.get("volumes"))
    for c in (toc.get("chapters") or [])[:8]:
        print(f"  卷[{c['volume']}] 第{c['index']}章 {c['title']}  {c['chars']}字  {c['file']}")
