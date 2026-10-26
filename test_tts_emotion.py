"""Synthesize the same lines through MiniMax with different emotions."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.providers.tts import build_tts

cfg = Config.load(r"E:\dramakit\config\default.yaml")
tts = build_tts(cfg.tts)
out = Path(r"C:\Users\David\AppData\Local\Temp\opencode\tts")
out.mkdir(parents=True, exist_ok=True)

voices = tts.list_voices()
print(f"provider={cfg.tts.provider} 可用中文音色 {len(voices)} 个")
print("  样例:", voices[:6])

LINES = [
    ("林凡", "male-qn-jingying", "林家，我回来了。", "愤怒"),
    ("林凡", "male-qn-jingying", "我回来了。", "坚定"),
    ("苏晚", "female-shaonv", "林凡？真的是你！", "惊讶"),
    ("苏晚", "female-shaonv", "这三年你去哪儿了？所有人都说你死了！", "悲伤"),
    ("林建国", "male-qn-badao", "爸，您糊涂了！他一个野种，凭什么继承林家？", "愤怒"),
    ("林老爷子", "Chinese (Mandarin)_Humorous_Elder", "凡儿……你终于回来了…", "悲伤"),
    ("旁白", "Chinese (Mandarin)_Radio_Host", "三年后。", "平静"),
]

emotion_map = cfg.tts.emotion_map
for spk, voice, text, emo in LINES:
    t0 = time.time()
    p = out / f"{spk}_{emo}.mp3"
    dur = tts.synthesize(text, voice, str(p),
                         emotion=emotion_map.get(emo, ""), speed=1.0)
    print(f"  {spk:6s} [{emo}] {emotion_map.get(emo,''):9s} "
          f"{dur:5.2f}s  {p.stat().st_size/1024:5.0f}KB  {time.time()-t0:5.1f}s")
