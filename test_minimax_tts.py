"""Can MiniMax T2A v2 give us emotional Chinese voices with the key we have?"""
import json
import urllib.request

KEY = "sk-cp-21ybJjlHsJm41qZL8jJxySDGJy91RZit0okb2KhYlcsyTMEnUh3cIR_h3vPM9Nbsni7wk_L0iZp4nTu8ahGn8xo0RQCd_za4B2YRuet4KkUxBU5SA27Ann4"
URL = "https://api.minimax.cn/v1/t2a_v2"


def call(model, voice, emotion, text="林家，我回来了。", out="mp3"):
    body = {
        "model": model,
        "text": text,
        "stream": False,
        "language_boost": "Chinese",
        "voice_setting": {"voice_id": voice, "speed": 1, "vol": 1, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000,
                          "format": out, "channel": 1},
    }
    if emotion:
        body["voice_setting"]["emotion"] = emotion
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}"
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"
    if "data" not in data:
        return f"无 data: {json.dumps(data, ensure_ascii=False)[:300]}"
    d = data["data"]
    return (f"OK extra={d.get('extra_info',{}).get('status')} "
            f"audio_len={len(d.get('audio',''))}")


print("1) speech-2.8-hd + 中文音色 + angry:")
print("  ", call("speech-2.8-hd", "Chinese (Mandarin)_Lyrical_Voice", "angry"))
print("2) speech-2.6-hd:")
print("  ", call("speech-2.6-hd", "Chinese (Mandarin)_Lyrical_Voice", "angry"))
print("3) speech-02-hd:")
print("  ", call("speech-02-hd", "Chinese (Mandarin)_Lyrical_Voice", "happy"))
print("4) male voice + sad:")
print("  ", call("speech-2.8-hd", "Chinese (Mandarin)_Male_Announcer", "sad"))
print("5) 不存在的音色（看错误格式）:")
print("  ", call("speech-2.8-hd", "no_such_voice_xyz", "sad"))

print("\n6) 音色列表接口:")
for ep in ("https://api.minimax.cn/v1/get_voice", "https://api.minimax.cn/v1/voice/list"):
    req = urllib.request.Request(ep, data=b"{}", headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.loads(r.read())
        print(f"   {ep} -> {json.dumps(d, ensure_ascii=False)[:400]}")
    except urllib.error.HTTPError as e:
        print(f"   {ep} -> HTTP {e.code} {e.read().decode('utf-8','replace')[:200]}")
    except Exception as e:  # noqa: BLE001
        print(f"   {ep} -> ERR {e}")
