"""Three more things the finished episode showed.

- The AIGC label was 64 pixels tall in the top left of a 1080 wide frame,
  right where the viewer looks first. It is a label, not a title: small,
  in the corner, out of the way of the faces.
- The storyboard let the ring jump: on the table, then in her hand, then
  in a box, then back on her finger. Props have to keep their state.
- In an over-the-shoulder shot the listener is in the foreground, and if
  their mouth is open the viewer hears the wrong person talking.
"""
from pathlib import Path

# 1) the AIGC label: small, in the corner, out of the way
p = Path(r"E:\\dramakit\\dramakit\\media\\ffmpeg.py")
s = p.read_text(encoding="utf-8")
old = """        label = (f"drawtext=fontfile='{font}':text='{text}':fontcolor=white@0.6:"
                 f"fontsize={watermark_size}"
                 f":x=24:y=20:box=1:boxcolor=black@0.35:boxborderw=6")"""
new = """        # a label, not a title: it belongs in the corner, small enough not
        # to take the attention the first second needs
        label = (f"drawtext=fontfile='{font}':text='{text}':fontcolor=white@0.55:"
                 f"fontsize={watermark_size}"
                 f":x=w-text_w-{max(16, width // 40)}:y={max(16, height // 90)}"
                 f":box=1:boxcolor=black@0.3:boxborderw={max(4, height // 180)}")"""
assert old in s, "水印锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("ffmpeg.py 已改（AI 声明缩小挪到右上）")

# the size follows the width now
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\compose.py")
s = p.read_text(encoding="utf-8")
old = "           watermark_size=max(14, cc.height // 30),"
new = "           watermark_size=max(12, cc.width // 52),"
assert old in s, "水印尺寸锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("compose.py 已改")

# 2) the props keep their state
p = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
s = p.read_text(encoding="utf-8")
old = """- **动作要跟着台词走**：镜头的动作描述必须和这一镜承载的台词对得上"""
new = """- **道具的状态要连贯**：戒指、杯子、手机、文件这些道具在每一镜的状态必须接得上
  上一镜（桌上 → 被拿起来 → 放进盒子 → 重新戴上），中间不能凭空跳变；
  桌上固定的东西（杯子几个、文件在谁手边）也不要换
- **动作要跟着台词走**：镜头的动作描述必须和这一镜承载的台词对得上"""
assert old in s, "道具锚点没找到"
s = s.replace(old, new, 1)

# 3) the listener keeps their mouth shut
old = """  txt += (f"画面里的 {'、'.join(others)} 只是听和反应："
          f"**嘴要闭着、不要张嘴、不要说话**"
          f"（keep their mouths closed, listening silently），"
          f"只给眼神和表情的反应。")"""
new = """  txt += (f"画面里的 {'、'.join(others)} 只是听和反应："
          f"**嘴要完全闭上、不许张开、不要露出牙齿、不要说话**"
          f"（keep their mouths fully closed, lips together, "
          f"listening silently），只给眼神和表情的反应。")"""
if old in s:
    s = s.replace(old, new, 1)
else:
    print("（说话人提示在另一个文件里，跳过）")
p.write_text(s, encoding="utf-8")
print("templates.py 已改")
