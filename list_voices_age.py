"""Find voices suited to an elderly man / an elder patriarch."""
import json
import urllib.request

KEY = "sk-cp-21ybJjlHsJm41qZL8jJxySDGJy91RZit0okb2KhYlcsyTMEnUh3cIR_h3vPM9Nbsni7wk_L0iZp4nTu8ahGn8xo0RQCd_za4B2YRuet4KkUxBU5SA27Ann4"
req = urllib.request.Request("https://api.minimax.cn/v1/get_voice",
                             data=json.dumps({"voice_type": "all"}).encode(),
                             headers={"Authorization": f"Bearer {KEY}",
                                      "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as r:
    d = json.loads(r.read())

HINTS = ("老", "爷", "长者", "学长", "大伯", "叔", "兄", "哥", "姐", "妹",
         "女", "男", "童", "少年", "青年", "中年", "主播", "有声", "新闻")
rows = [(v.get("voice_id", ""), v.get("voice_name", ""))
        for v in d.get("system_voice") or []]
print(f"全部 {len(rows)} 个音色，含年龄/性别提示的：")
for vid, name in rows:
    if any(h in name for h in HINTS):
        print(f"  {vid:52s} {name}")
