"""Can MiniMax generate the music instead of H3 doing it?

The drama kit records the dialogue itself, so the only thing the video
model's own audio is good for is the score - and it cannot do that without
speaking over the dialogue. MiniMax has a music model; if it works, the
score comes from there and the video's own sound is free to do the lip
movement.
"""
import json
import sys
import time

sys.path.insert(0, r"E:\dramakit")
import httpx
from dramakit.config import Config

cfg = Config.load(r"E:\dramakit\config\default.yaml")
key = cfg.tts.api_key
base = cfg.tts.base_url.rstrip("/")

PROMPT = ("Chinese short drama score, cinematic tension, low piano and "
          "strings, slow build, no vocals, no lyrics, no singing")

for path, payload in (
    ("/v1/music_generation",
     {"model": "music-01", "prompt": PROMPT, "audio_length": 60}),
    ("/v1/music_generation?GroupId=",
     {"model": "music-01", "prompt": PROMPT, "audio_length": 60}),
):
    url = base + path
    try:
        r = httpx.post(url, json=payload, headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"},
            timeout=180.0, trust_env=False)
        body = r.text[:600]
        print(f"[{r.status_code}] {url}\n    {body}\n")
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                continue
            d = data.get("data") or {}
            print("    字段:", list(d)[:12])
            if d.get("audio"):
                print("    音频长度(hex):", len(d["audio"]))
            break
    except Exception as e:  # noqa: BLE001
        print(f"异常 {url}: {type(e).__name__} {str(e)[:160]}")
