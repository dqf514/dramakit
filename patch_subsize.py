"""The subtitle has to fit the frame it is in.

The font was scaled with the height of the picture, which is right for a
wide frame and wrong for a tall one: in a 1080x1920 frame it came out at
107 pixels, and a fourteen character line needed 1498 pixels of the 1080
there are. The size is now worked out from the width - the line has to fit
sideways - and from the longest line there is.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\media\\subtitle.py")
s = p.read_text(encoding="utf-8")

# 1) the header takes the longest line into account
old = """def _ass_header(style: dict, width: int, height: int) -> str:"""
new = """def _text_width(text: str) -> float:
    \"\"\"How wide a line is, in characters: a Chinese one is a full width.\"\"\"
    total = 0.0
    for ch in text or "":
        total += 1.0 if ord(ch) > 0x2E80 else 0.55
    return total


def _ass_header(style: dict, width: int, height: int,
                longest: float = 0.0) -> str:"""
assert old in s, "头部锚点没找到"
s = s.replace(old, new, 1)

old = """    k = height / 288
    scaled = int(round(size * k))
    narr_scaled = int(round(narr_size * k))"""
new = """    # The size follows the width of the picture: a line has to fit
    # sideways, and in a tall frame a size taken from the height runs off
    # both edges.
    k = width / 960.0
    scaled = int(round(size * k))
    if longest > 0:
        room = (width - 2 * int(round(60 * height / 1080))) / longest
        scaled = max(12, min(scaled, int(room * 0.95)))
    narr_scaled = int(round(narr_size * k))"""
assert old in s, "字号锚点没找到"
s = s.replace(old, new, 1)

# 2) the writer measures its own lines
old = """    parts = [_ass_header(style, width, height)]"""
new = """    longest = 0.0
    for c in cues:
        if c.kind in (LineKind.NARRATION, LineKind.CAPTION):
            continue
        longest = max(longest, _text_width(_clean(c.text)))
    parts = [_ass_header(style, width, height, longest)]"""
assert old in s, "写入锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("subtitle.py 已改（字号按宽度定）")
