"""The font size is a share of the picture's width.

The base of 16 was for a 288 high canvas, which was a wide frame. In a
tall frame the size has to follow the width: the line has to fit
sideways. 30 pixels on a 960 wide frame is what the episodes have always
looked like.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = "    font_size: 16                           # 内部按分辨率放大"
new = "    font_size: 30                           # 以 960 宽为基准，按画面宽度放大"
assert old in s, "字号锚点没找到"
s = s.replace(old, new, 1)
old = "    narration_font_size: 14"
new = "    narration_font_size: 26"
assert old in s, "旁白字号锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml 已改")

p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = '        "font_size": 16,'
new = '        "font_size": 30,          # 以 960 宽为基准，按画面宽度放大'
assert old in s, "config 字号锚点没找到"
s = s.replace(old, new, 1)
old = '        "narration_font_size": 14,'
if old in s:
    s = s.replace(old, '        "narration_font_size": 26,', 1)
p.write_text(s, encoding="utf-8")
print("config.py 已改")
