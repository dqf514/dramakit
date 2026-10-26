"""Find the MiniMax Chinese system voices that work, for cast diversity."""
import json
import urllib.request

KEY = "sk-cp-21ybJjlHsJm41qZL8jJxySDGJy91RZit0okb2KhYlcsyTMEnUh3cIR_h3vPM9Nbsni7wk_L0iZp4nTu8ahGn8xo0RQCd_za4B2YRuet4KkUxBU5SA27Ann4"
HEAD = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

print("=== get_voice 各种参数 ===")
for body in ({"voice_type": "all"}, {"voice_type": "system"}, {"type": "all"},
             {"voice_type": "all", "page_size": 200}, {"need_volcengine_type": 1}):
    req = urllib.request.Request("https://api.minimax.cn/v1/get_voice",
                                 data=json.dumps(body).encode(), headers=HEAD)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.loads(r.read())
        sv = d.get("system_voice") or []
        print(f"  {body} -> system_voice={len(sv)}  status={d.get('base_resp',{}).get('status_msg')}")
        if sv:
            print("     样例:", json.dumps(sv[0], ensure_ascii=False)[:300])
            print("     全部:", json.dumps([v.get("voice_id") for v in sv],
                                          ensure_ascii=False)[:2000])
            break
    except urllib.error.HTTPError as e:
        print(f"  {body} -> HTTP {e.code} {e.read().decode('utf-8','replace')[:150]}")
    except Exception as e:  # noqa: BLE001
        print(f"  {body} -> ERR {e}")

print("\n=== 候选音色逐个试探 ===")
CANDIDATES = [
    "Chinese (Mandarin)_Lyrical_Voice", "Chinese (Mandarin)_Male_Announcer",
    "Chinese (Mandarin)_Gentleman", "Chinese (Mandarin)_Sweet_Lady",
    "Chinese (Mandarin)_Warm_Bestie", "Chinese (Mandarin)_Breezy_Lady",
    "Chinese (Mandarin)_Sweet_Girl", "Chinese (Mandarin)_AspiringYouth",
    "Chinese (Mandarin)_Youth_Sunshine", "Chinese (Mandarin)_SincereTeen",
    "Chinese (Mandarin)_Magical_Voice", "Chinese (Mandarin)_Sweet_Serene_Woman",
    "Chinese (Mandarin)_Warm_Woman", "Chinese (Mandarin)_News_Anchor",
    "Chinese (Mandarin)_Mature_Woman", "Chinese (Mandarin)_Elderly_Man",
    "Chinese (Mandarin)_Honest_Man", "Chinese (Mandarin)_Stubborn_Friend",
    "Chinese (Mandarin)_Wounded_Youth", "Chinese (Mandarin)_Youth_Man",
    "male-qn-qingse", "male-qn-jingying", "male-qn-badao", "male-qn-daxuesheng",
    "female-shaonv", "female-chengshu", "female-yueyue",
    "presenter_male", "presenter_female", "audiobook_male_1", "audiobook_female_1",
    "Chinese (Mandarin)_Cold_Girl", "Chinese (Mandarin)_Pure_Elderly_Man",
    "Chinese (Mandarin)_Infant_Man", "Chinese (Mandarin)_Brave_Girl",
]


def ok(voice):
    body = {"model": "speech-2.8-hd", "text": "测试", "stream": False,
            "language_boost": "Chinese",
            "voice_setting": {"voice_id": voice, "speed": 1, "vol": 1, "pitch": 0},
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000,
                              "format": "mp3", "channel": 1}}
    req = urllib.request.Request("https://api.minimax.cn/v1/t2a_v2",
                                 data=json.dumps(body).encode(), headers=HEAD)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        return len(d.get("data", {}).get("audio", "")) > 0
    except Exception:  # noqa: BLE001
        return False


good = [v for v in CANDIDATES if ok(v)]
print("可用的中文音色:", len(good))
for v in good:
    print("   ", v)
