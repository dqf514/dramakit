"""Put the mouth-sync settings into the yaml."""
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = "  film_grain: 4                            # 胶片颗粒强度（去掉 AI 塑料感，0=关）"
new = """  film_grain: 4                            # 胶片颗粒强度（去掉 AI 塑料感，0=关）
  # 口型对齐：画面里的嘴由模型自己动，录好的声音和嘴对不上，
  # 观众就会觉得声音飘在画面外。MuseTalk 用录好的音频重画嘴。
  lipsync: false                           # 打开后每个有台词的镜头都会过一遍 MuseTalk
  musetalk_root: "E:\\musetalk"            # MuseTalk 的代码与权重
  musetalk_python: "E:\\ComfyUI\\venv\\Scripts\\python.exe"
  lipsync_timeout: 900                     # 一个镜头的口型对齐最多等多久（秒）"""
assert old in s, "film_grain 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml 已改")
