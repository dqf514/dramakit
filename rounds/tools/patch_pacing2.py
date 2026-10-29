"""The last two pieces: the window for the line, and the QA limits."""
from pathlib import Path

# 4) the prompt: say the line inside the window, with room at the end
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")
old = """    out = []
    at = 0.0
    for spk, _txt, d in lines[:4]:
        length = float(d) if d and d > 0 else 0.0
        if length <= 0:
            length = dur / len(lines)
        out.append(f"{at:.1f}-{at + length:.1f}秒：{spk} 开口说这句台词")
        at += length
    if at < dur - 0.05:
        out.append(f"{at:.1f}-{dur:.1f}秒：保持情绪与姿态")
    return "；".join(out)"""
new = """    out = []
    at = 0.0
    for spk, _txt, d in lines[:4]:
        length = float(d) if d and d > 0 else 0.0
        if length <= 0:
            length = dur / len(lines)
        # the model speaks slower than the recording, so the line gets a
        # little more room than it needs, and it is told to finish in it
        window = length * 1.15 + 0.15
        out.append(f"{at:.1f}-{at + window:.1f}秒：{spk} 开口说这句台词"
                   f"（**在这段时间里说完，不要拖到后面**）")
        at += window
    if at < dur - 0.05:
        out.append(f"{at:.1f}-{dur:.1f}秒：说完后保持情绪与姿态，"
                   f"给对方一点反应的时间")
    return "；".join(out)"""
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
else:
    print("（平均镜头阈值没找到）")
p.write_text(s, encoding="utf-8")
print("qa.py: 节奏阈值放宽")
