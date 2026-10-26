"""Is MiniMax's data.audio hex or base64? And what does the mp3 look like?"""
import base64
import json
import urllib.request

KEY = "sk-cp-21ybJjlHsJm41qZL8jJxySDGJy91RZit0okb2KhYlcsyTMEnUh3cIR_h3vPM9Nbsni7wk_L0iZp4nTu8ahGn8xo0RQCd_za4B2YRuet4KkUxBU5SA27Ann4"
body = {
    "model": "speech-2.8-hd",
    "text": "林家，我回来了。",
    "stream": False,
    "language_boost": "Chinese",
    "voice_setting": {"voice_id": "male-qn-qingse", "speed": 1, "vol": 1,
                      "pitch": 0, "emotion": "angry"},
    "audio_setting": {"sample_rate": 32000, "bitrate": 128000,
                      "format": "mp3", "channel": 1},
}
req = urllib.request.Request("https://api.minimax.cn/v1/t2a_v2",
                             data=json.dumps(body).encode(),
                             headers={"Authorization": f"Bearer {KEY}",
                                      "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=90) as r:
    d = json.loads(r.read())
audio = d["data"]["audio"]
print("audio 字符串长度:", len(audio), " 前 32 字符:", audio[:32])
for name, dec in (("hex", bytes.fromhex), ("base64", base64.b64decode)):
    try:
        raw = dec(audio)
        print(f"  {name}: {len(raw)} 字节  头 {raw[:4]!r}  "
              f"像mp3: {raw[:3] == b'ID3' or raw[:2] in (b'\\xff\\xfb', b'\\xff\\xf3')}")
    except Exception as e:  # noqa: BLE001
        print(f"  {name}: 解不开 {e}")
print("extra_info:", json.dumps(d["data"].get("extra_info"), ensure_ascii=False)[:300])
print("完整响应字段:", list(d.keys()), list(d.get("data", {}).keys()))
