"""A shot becomes a segment, and the model cuts inside it.

The video model makes a clip of several seconds that contains several
shots - the cut times are given inside the prompt. Our storyboard was
splitting per line instead, so every line got its own two second cut:
that is what made the episode feel dizzy and unharmonious.

So a "shot" in our table is now a segment: six to fifteen seconds, with
the shots inside it written into the action, and the cut times left to
the model.
"""
from pathlib import Path

# 1) the config: a segment is 6-15 seconds
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    # 镜头可以很长：一句台词说完，镜头可以停在脸上继续演
    shot_duration_range: list[float] = Field(default_factory=lambda: [2.5, 15.0])"""
new = """    # 一个片段的长度：视频模型一次出一段，段里可以有好几个镜头，
    # 切点由提示词里的时间戳决定。2 秒一切看着晕，所以片段要长。
    shot_duration_range: list[float] = Field(default_factory=lambda: [6.0, 15.0])"""
assert old in s, "时长区间锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py: 片段 6~15 秒")

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = "  shot_duration_range: [2.5, 15.0]"
new = "  shot_duration_range: [6.0, 15.0]            # 一个片段 6~15 秒，段里有多个镜头"
assert old in s, "yaml 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml: 片段 6~15 秒")

# 2) the storyboard: a row is a segment with shots inside it
p = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
s = p.read_text(encoding="utf-8")

old = """- duration: 该镜头秒数（{{dur_min}}~{{dur_max}}秒；对白镜头时长要够说完对应台词）
- action: 画面内容中文描述，**必须写清三件事**：①谁在画面里（姓名）②在什么地方
  （场景+时间）③这个人正在做什么（动作、表情、视线）。这三件事写不清，
  后面生成的时候模型就得自己编，人物和场景就会跑掉"""
new = """- duration: 该片段秒数（{{dur_min}}~{{dur_max}}秒；一个片段里可以有好几个镜头，
  视频模型会在片段内部按你写的切点切）
- action: 这个片段里发生了什么，中文描述。**必须写清三件事**：①谁在画面里
  （姓名）②在什么地方（场景+时间）③这个人正在做什么（动作、表情、视线）。
  如果片段里有多个镜头，就按顺序写：「镜头1：…；镜头2：…；镜头3：…」，
  每个镜头都要有自己的景别和机位（近景/过肩/特写…），不要整段一个景别"""
assert old in s, "duration 锚点没找到"
s = s.replace(old, new, 1)

old = """- **节奏：一个镜头承载的对白不超过 4.5 秒**：一句台词，或者两句短的
  （同一个说话人，中间要留出半秒的停顿——镜头不急着切，让观众听清楚）。
  换了说话人就切镜（正反打），观众才跟得上谁在说。
  **不要一句一镜**：连着几句台词可以留在同一个镜头里（对话戏的镜头常常停很久），
  但一句话说完之后要给对方一点反应的时间。连续两个超过 5 秒的镜头会让观众划走。"""
new = """- **节奏：一个片段承载的对白不超过 8 秒**（通常 2~4 句），
  片段内部再分镜：一句话说完给半秒的停顿，**不要一句一切**。
  段内切点要跟着台词走：换说话人就切（正反打），同一个人连着说就别切。
  连续两个超过 12 秒的片段会让观众划走。"""
assert old in s, "节奏锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("templates.py: 片段制")

# 3) the prompt to H3: the shots inside the segment and their cut times
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")
old = '''                    "overall_soundscape 写环境声和动作声，不要写人声。")'''
new = '''                    "overall_soundscape 写环境声和动作声，不要写人声。"
                    "**这一段里可以有好几个镜头**：用 [Shot 1]、[Shot 2] 写，"
                    "后面的镜头用 `At 00:0X.000, the camera cuts to ...` 标出切点；"
                    "每个镜头要有自己的景别和机位，不要整段一个景别。")'''
assert old in s, "native note 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py: 段内多镜头")

# 4) the QA: the limits are for segments now
p = Path(r"E:\\dramakit\\qa.py")
s = p.read_text(encoding="utf-8")
old = """        limit = 5.0 if len(lines) <= 1 else 6.5"""
new = """        limit = 12.0 if len(lines) <= 1 else 16.0"""
assert old in s, "节奏阈值锚点没找到"
s = s.replace(old, new, 1)
old = """    if p["avg_shot"] > 4.0:"""
new = """    if p["avg_shot"] > 11.0:"""
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("qa.py: 阈值按片段")
