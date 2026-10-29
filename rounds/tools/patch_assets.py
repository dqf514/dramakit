"""The character asset sheet, the way the tutorial does it.

The teacher says it plainly: give every character one standard reference
picture first - the front, the back, the clothes, the hair, the details
all in one image - and treat it as the costume. Whatever scene or action
comes later, the person comes from that sheet. Our sheet had no back
view, so a character seen from behind had nothing to hold on to.
"""
from pathlib import Path

# 1) the back view
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\character.py")
s = p.read_text(encoding="utf-8")
old = """VIEW_TEXT = {
    "front": "front view, facing the camera, neutral standing pose",
    "side": "side profile view, facing left, neutral standing pose",
    "three_quarter": "three-quarter view, slight body angle, neutral standing pose",
}"""
new = """VIEW_TEXT = {
    "front": "front view, facing the camera, neutral standing pose",
    "side": "side profile view, facing left, neutral standing pose",
    "three_quarter": "three-quarter view, slight body angle, neutral standing pose",
    "back": "back view, seen from behind, neutral standing pose",
}"""
assert old in s, "VIEW_TEXT 锚点没找到"
s = s.replace(old, new, 1)

old = """FLUX3_VIEW = {
    "front": "seen from the front, facing the camera, standing at ease",
    "side": "seen from the side in profile, facing left, standing at ease",
    "three_quarter": "seen from a three-quarter angle, body slightly turned, standing at ease",
}"""
new = """FLUX3_VIEW = {
    "front": "seen from the front, facing the camera, standing at ease",
    "side": "seen from the side in profile, facing left, standing at ease",
    "three_quarter": "seen from a three-quarter angle, body slightly turned, standing at ease",
    "back": "seen from behind, back turned to the camera, standing at ease",
}"""
assert old in s, "FLUX3_VIEW 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("character.py: 加了背面视图")

# 2) the config: the views and the sheet
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    ref_views: list[str] = Field(default_factory=lambda: ["front", "side", "three_quarter"])"""
new = """    # 正面、侧面、四分之三、背面：一张资产图上拼起来，人物全程不变
    ref_views: list[str] = Field(
        default_factory=lambda: ["front", "side", "three_quarter", "back"])"""
assert old in s, "ref_views 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py: 四视图")

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = "  ref_views: [front, side, three_quarter]"
new = "  ref_views: [front, side, three_quarter, back]   # 角色资产图：正面/侧面/四分之三/背面"
if old in s:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("yaml: 四视图")
else:
    print("yaml: 没找到 ref_views（用 config 的默认值）")

# 3) the shot description: who, where, what
p = Path(r"E:\\dramakit\\dramakit\\prompts\templates.py")
s = p.read_text(encoding="utf-8")
old = """- action: 画面内容中文描述（谁、在哪、做什么、什么表情）"""
new = """- action: 画面内容中文描述，**必须写清三件事**：①谁在画面里（姓名）②在什么地方
  （场景+时间）③这个人正在做什么（动作、表情、视线）。这三件事写不清，
  后面生成的时候模型就得自己编，人物和场景就会跑掉"""
assert old in s, "action 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("templates.py: 镜头描述三要素")
