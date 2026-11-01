"""Does the upload endpoint take a book?"""
import json
import urllib.request

body = json.dumps({
    "name": "测试小说",
    "text": "第一章 遇见\n\n这是第一章的正文。" * 40 +
            "\n第二章 离别\n\n这是第二章的正文。" * 40,
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:8080/api/upload", data=body,
    headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=300) as r:
    d = json.loads(r.read())
print("ok:", d.get("ok"))
print("项目:", d.get("project"))
print("字数:", d.get("chars"))
print("catalog:", d.get("catalog"))
print("catalog_error:", d.get("catalog_error"))
