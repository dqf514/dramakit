"""The screenplay prompt, with the inner voice where it belongs.

The book is written in the first person - "I was sure it was only a
nightmare" - and that narration is the character's inner voice: it is
heard, and nobody else hears it.  The quotes in the book are what is
said out loud.  So the prompt says which is which, and the line rule
stops chopping one sentence into three.
"""
import pathlib

P = pathlib.Path(r"E:\dramakit\dramakit\prompts\templates.py")
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

# ---- the plan: a scene is a place and a time ----------------------------- #
old = """约束：
- 每一场只有三样东西：**场景、一段动作、拍**。"""
new = """约束：
- **拆成 {{min_scenes}}~{{max_scenes}} 场；同一时空为一场**——地点和时间都
  相同的就是一场，不要把一次对话拆成几场，也不要把一场拆到几个地方去。
- 每一场只有三样东西：**场景、一段动作、拍**。"""
assert old in text
text = text.replace(old, new, 1)

# ---- the scene: the lines, and the voice that is not spoken -------------- #
old = """- **对白**（kind=dialogue）：角色（提示）：台词，一句不超过 12 个字。
  - **心里的话**（kind=voice_over）：这个人**没有开口**，声音只在他自己心里
    响——观众听得见，别的角色听不见。这是心理活动的标准写法；能用一个
    动作或一句台词说清楚的，就不要用它。一场戏最多两句。
  - **画外对白**（kind=off_screen）：这个人**在画面外**说话（门那边、楼下、
    远处），人不出画。
  - **旁白**（kind=narration）：只交代必要的时空和身份，不重复画面已经
    说出来的。"""
new = """- **对白**（kind=dialogue）：原文里带引号的那些话，是说出口的。
  一句台词是一个完整的话，**不要把一句话拆成几段**；短的可以两三个字，
  长的可以到二十个字。
- **心里的话**（kind=voice_over）：**原文里没有引号的第一人称叙述**，就是
  这个角色心里的话——他**没有开口**，声音只在他自己心里响，观众听得见、
  别的角色听不见。这是心理活动的标准写法，也是这本书的叙述方式。
  保留原文的第一人称"我"，写清楚他此刻在想什么。
  能用动作或一句台词说清楚的，就不要用它。
- **画外对白**（kind=off_screen）：这个人**在画面外**说话（门那边、楼下、
  远处），人不出画。在场的人说话是 dialogue，不是 off_screen。
- **旁白**（kind=narration）：只交代必要的时空和身份，不重复画面已经
  说出来的。"""
assert old in text
text = text.replace(old, new, 1)

old = """- 台词之间要有来回，不是各说各的；要有一句扎人的话——不是最狠的那句，
  是最准的那句，一句话就把这场的劲顶起来；每个人说话像他自己，此刻他
  想要什么、怕什么、瞒什么。括号里的表演提示写进 emotion，不要写进
  text——text 会被配音念出来，也会变成字幕。"""
new = """- 台词之间要有来回，不是各说各的；要有一句扎人的话——不是最狠的那句，
  是最准的那句，一句话就把这场的劲顶起来；每个人说话像他自己，此刻他
  想要什么、怕什么、瞒什么。括号里的表演提示写进 emotion，不要写进
  text——text 会被配音念出来，也会变成字幕。
- **心里的话和说出口的话要有分工**：说了出口的，就不要再用心里的话
  重复一遍；心里的话只给画面给不出来的那些东西（她记得什么、她怕什么、
  她算到了什么）。"""
assert old in text
text = text.replace(old, new, 1)

if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("场景划分、台词切分、心里话都改了")
