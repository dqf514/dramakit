"""The scene has to be the same scene in every shot.

The location's visual prompt said "warm wood and dark marble table", and
FLUX 3 picked one or the other for each shot - so the table the couple
sat at was wood in one shot and marble in the next. The description of a
location has to name one of everything, and the prompt has to say that
the reference picture decides.
"""
from pathlib import Path

# 1) the analyze prompt: one of everything
p = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
s = p.read_text(encoding="utf-8")
old = """- locations: 主要场景（最多{{max_locations}}个）: name, description, visual_prompt(英文)"""
new = """- locations: 主要场景（最多{{max_locations}}个）: name, description, visual_prompt(英文)
  - **visual_prompt 必须唯一**：每样东西只写一种——一种桌子材质、一个主色调、
    一种地板。写成 "wood and marble table" 的话，每一镜的画都会挑一种，
    桌子就在木纹和大理石之间跳。还要写死固定物��的位置：窗在左还是右、
    卡座在哪边、背景是什么，写清楚之后每一镜都照着来"""
assert old in s, "场景锚点没找到"
s = s.replace(old, new, 1)

# 2) the image prompt: the reference decides
old = """场景设定（保持一致，不要改建筑风格/陈设）：{{location_visual}}"""
new = """场景设定（保持一致，不要改建筑风格/陈设）：{{location_visual}}
（**场景参考图是唯一标准**：桌子的材质和颜色、窗户在哪边、座位怎么排、
背景里有什么，都照着参考图来，不要换、不要重新设计）"""
assert old in s, "出图场景锚点没找到"
s = s.replace(old, new, 1)

# 3) the H3 prompt: the same
old = """场景设定（保持一致）：{{location_visual}}"""
new = """场景设定（保持一致）：{{location_visual}}
（场景参考图是唯一标准：桌子的材质和颜色、窗户位置、座位关系都不要变）"""
assert old in s, "H3 场景锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("templates.py 已改")
