"""Does the cut find chapters in a book that has them?"""
import json
import urllib.request

# a book shaped like a real one: volume markers, chapter markers, and body
novel = ""
for vol, chapters in [("卷一 少年", range(1, 4)), ("卷二 崛起", range(4, 7))]:
    novel += f"\n{vol}\n\n"
    for i in chapters:
        novel += f"第{i}章 初醒\n\n" + ("苏晚睁开眼睛，发现自己回到了婚礼现场。" * 20) + "\n"

body = json.dumps({"name": "分卷测试6", "text": novel}).encode("utf-8")
req = urllib.request.Request(
    "http://127.0.0.1:8080/api/upload", data=body,
    headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=300) as r:
    d = json.loads(r.read())
print("ok:", d.get("ok"), "| 项目:", d.get("project"), "| 字数:", d.get("chars"))
cat = d.get("catalog") or {}
print("切分:", cat)

slug = d.get("project") or ""
if slug and cat.get("chapters"):
    req2 = urllib.request.Request(
        "http://127.0.0.1:8080/api/catalog",
        data=json.dumps({"project": slug}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req2, timeout=60) as r2:
        toc = json.loads(r2.read())
    print("卷:", toc.get("volumes"))
    for c in (toc.get("chapters") or [])[:8]:
        print(f"  卷[{c['volume']}] 第{c['index']}章 {c['title']}  {c['chars']}字  {c['file']}")
