"""Put the drift rules in the system prompt - they are followed there."""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\prompts\templates.py")
s = p.read_text(encoding="utf-8")

old = """- 不要写 negative prompt，不要出现 "no text"、"without watermark" 这类否定描述
- 画面是 16:9 横屏\"\"\""""
new = """- 不要写 negative prompt，不要出现 "no text"、"without watermark" 这类否定描述
- **integrated_multimodal_description 的结尾必须原样写上这些约束**（写在描述的最后）：
  保持人物身份、脸部、发型与服装和第一帧完全一致；画面里不出现除第一帧已有文字以外的新文字，
  也不加字幕和水印；不出现多余人物、多余肢体或畸形的手；镜头不抖动、不跳帧、不慢动作；
  不要切换到别的场景或别的机位。
- **描述里要写清楚时间轴**（例如 "From 0.0 to 2.0 seconds, ..."），
  各段时间之和必须等于本镜时长；还要写明角色说话时的口型动作（opens her mouth and speaks），
  台词由后期配音轨提供，画面里的口型要对得上。
- 画面是 16:9 横屏\"\"\""""
assert old in s, "系统提示锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("templates.py 已打补丁")
