import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.project import ProjectStore
from dramakit.media import ffmpeg as ff

cfg = Config.load(r"E:\dramakit\config\default.yaml")
store = ProjectStore(Path(r"E:\dramakit\projects\测试短剧"))
proj = store.load()

print("=== 选角 ===")
seen = {}
for c in proj.characters:
    seen.setdefault(c.voice_id, []).append(c.name)
    print(f"  {c.name:6s} {c.role or '':8s} {c.voice_id:42s} "
          f"pitch={c.voice_pitch or '-'} rate={c.voice_rate or '-'}")
dupes = {v: n for v, n in seen.items() if len(n) > 1}
print("  重复音色:", dupes or "无")

print("\n=== 逐句（情绪 / 实际时长 vs 标注）===")
for ep in proj.episodes[:1]:
    for sc in ep.scenes:
        for l in sc.lines:
            if not l.audio_path:
                print(f"  旁白 [{l.emotion}]  (仅屏幕文字) {l.text[:26]}")
                continue
            d = ff.probe_duration(store.abs(l.audio_path))
            emo = cfg.tts.emotion_map.get(l.emotion, "-")
            print(f"  {(l.speaker or '旁白'):6s} [{l.emotion:4s}->{emo:9s}] "
                  f"{d:5.2f}s  {l.text[:26]}")
