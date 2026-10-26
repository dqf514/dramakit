import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.voice import _emotion_key

cfg = Config.load(r"E:\dramakit\config\default.yaml")
print("情绪标签 -> 映射结果:")
labels = ["冷笑（愤怒）", "犹豫（心虚）", "公事公办（平静）", "愤怒（咬牙）",
          "冷静（意味深长）", "决绝（平静）", "诱劝（紧张）", "焦急",
          "隐藏的喜悦", "震怒", "平静"]
for e in labels:
    k = _emotion_key(cfg, e)
    provider = cfg.tts.emotion_map.get(k, "-")
    mod = (cfg.tts.emotion_modulation or {}).get(k, {})
    print(f"   {e:<16} -> {k:<6} provider={provider:<10} 调制={mod or '无'}")
