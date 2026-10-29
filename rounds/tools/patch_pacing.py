"""Give the episode room to breathe.

The cuts came too often - one per line - and the pauses between lines
were too short to feel like a person thinking. And H3 speaks slower than
the recording, so the words ran past the end of the clip and got cut off
mid-sentence.

So: a shot may carry two lines again, the breath between lines is longer,
and the prompt tells the model to finish the line inside the window it
was given, with a little room at the end of the shot.
"""
from pathlib import Path

# 1) the pause between lines
p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = "  line_gap: 0.35                            # 每句台词之间的留白（秒）"
new = "  line_gap: 0.5                             # 每句台词之间的留白（秒）"
assert old in s, "line_gap 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml: 留白 0.35 -> 0.5")

p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    line_gap: float = 0.35"""
new = """    line_gap: float = 0.5"""
assert old in s, "config line_gap 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py: 留白 0.5")

# 2) a shot may carry two lines again
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\base.py")
s = p.read_text(encoding="utf-8")
old = """SHOT_DIALOGUE_MAX = 3.5"""
new = """SHOT_DIALOGUE_MAX = 4.5"""
assert old in s, "SHOT_DIALOGUE_MAX 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("base.py: 单镜对白上限 4.5 秒")

# 3) the storyboard: two lines in a shot are welcome again
p = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
s = p.read_text(encoding="utf-8")
old = """- **节奏：一个镜头承载的对白不超过 3.5 秒，通常就是 1 句台词**（只有一句特别短时
  才带两句，而且必须是同一个说话人）。换了说话人就切镜（正反打），观众才跟得上谁在说；
  短剧的镜头平均 2~3 秒一刀，台词多的地方要拆成更多镜头，镜头短、节奏快，
  是短剧留人的关键。连续两个超过 4 秒的镜头会让观众划走。"""
new = """- **节奏：一个镜头承载的对白不超过 4.5 秒**：一句台词，或者两句短的
  （同一��说话人，中间要留出半秒的停顿——镜头不急着切，让观众听清楚）。
  换了说话人就切镜（正反打），观众才跟得上谁在说。
  **不要一句一镜**：连着几句台词可以留在同一个镜头里（对话戏的镜头常常停很久），
  但一句话说完之后要给对方一点反应的时间。连续两个超过 5 秒的镜头会让观众划走。"""
assert old in s, "节奏规则锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("templates.py: 允许一镜两句")

# 4) the prompt: say the line inside the window, with room at the end
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")
old = '''    out = []
    at = 0.0
    for spk, _txt, d in lines[:4]:
        length = float(d) if d and d > 0 else 0.0
        if length <= 0:
            length = dur / len(lines)
        out.append(f"{at:.1f}-{at + length:.1f}秒：{spk} 开口说这句台词")
        at += length
    if at < dur - 0.05:
        out.append(f"{at:.1f}-{dur:.1f}秒：保持情绪与姿态")
    return "；".join(out)'''
new = '''    out = []
    at = 0.0
    for spk, _txt, d in lines[:4]:
        length = float(d) if d and d > 0 else 0.0
        if length <= 0:
            length = dur / len(lines)
        # the model speaks slower than the recording, so give the line a
        # little more room than it needs, and say so
        window = length * 1.15 + 0.15
        out.append(f"{at:.1f}-{at + window:.1f}秒：{spk} 开口说这句台词"
                   f"（**在这段时间里说完，不要拖到后面**）")
        at += window
    if at < dur - 0.05:
        out.append(f"{at:.1f}-{dur:.1f}秒：说完后保持情绪与姿态，"
                   f"给对方一点反应的时间")
    return "；".join(out)'''
assert old in s, "时间轴锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py: 台词按窗口说完")

# 5) the QA: a shot with two lines may be longer
p = Path(r"E:\\dramakit\\qa.py")
s = p.read_text(encoding="utf-8")
old = """        limit = 4.0 if len(lines) <= 1 else 5.0"""
new = """        limit = 5.0 if len(lines) <= 1 else 6.5"""
assert old in s, "节奏阈值锚点没找到"
s = s.replace(old, new, 1)
old = """    if p["avg_shot"] > 3.5:"""
new = """    if p["avg_shot"] > 4.0:"""
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("qa.py: 节奏阈值放宽")
