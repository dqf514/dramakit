"""Does the console now serve the clickable node address?"""
import urllib.request

req = urllib.request.Request("http://127.0.0.1:8080/",
                             headers={"Cache-Control": "no-cache"})
with urllib.request.urlopen(req, timeout=30) as r:
    body = r.read().decode("utf-8")
    print("  Cache-Control:", r.headers.get("Cache-Control"))
print("  页面里有 nodeLink:", "nodeLink" in body)
print("  用到 nodeLink 的次数:", body.count("nodeLink(n.base_url)"))
print("  旧的纯文本写法还在:",
      'style="font-weight:400;font-size:11px">${esc(n.base_url)}' in body)
