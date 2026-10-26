"""List the Chinese MiniMax voices with their names, for casting."""
import json
import urllib.request

KEY = "sk-cp-21ybJjlHsJm41qZL8jJxySDGJy91RZit0okb2KhYlcsyTMEnUh3cIR_h3vPM9Nbsni7wk_L0iZp4nTu8ahGn8xo0RQCd_za4B2YRuet4KkUxBU5SA27Ann4"
req = urllib.request.Request("https://api.minimax.cn/v1/get_voice",
                             data=json.dumps({"voice_type": "all"}).encode(),
                             headers={"Authorization": f"Bearer {KEY}",
                                      "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as r:
    d = json.loads(r.read())

rows = []
for v in d.get("system_voice") or []:
    vid = v.get("voice_id", "")
    name = v.get("voice_name", "")
    if "Chinese" in vid or vid.startswith(("male-", "female-")) or \
            vid.startswith(("presenter_", "audiobook_")):
        rows.append((vid, name))

print(f"中文相关音色 {len(rows)} 个：")
for vid, name in rows:
    print(f"  {vid:52s} {name}")
