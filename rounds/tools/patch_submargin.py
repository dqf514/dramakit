"""Put the subtitle where the platform's own buttons are not.

In a tall frame the subtitle that sits one text height above the bottom
edge ends up under the platform's own buttons - the account name and the
like row cover the bottom of a vertical drama. The margin can be given as
a share of the height instead, so it stays clear of them in any frame.
"""
from pathlib import Path

# 1) the subtitle style
p = Path(r"E:\\dramakit\\dramakit\\media\\subtitle.py")
s = p.read_text(encoding="utf-8")
old = """    heights = float(margin_v or 1)
    margin_v = int(round(scaled * heights))"""
new = """    heights = float(margin_v or 1)
    margin_v = int(round(scaled * heights))
    # a share of the height: in a tall frame the bottom is where the
    # platform's own buttons sit, so the subtitle has to clear them
    pct = float(style.get("margin_v_pct") or 0)
    if pct > 0:
        margin_v = max(margin_v, int(round(height * pct / 100.0)))"""
assert old in s, "字幕边距锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("subtitle.py 已改")

# 2) the config
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    margin_v: int = 1"""
new = """    margin_v: int = 1
    # 字幕离画面底部的百分比：竖屏里底部是平台自己的按钮区，字幕要避开
    margin_v_pct: float = 12.0"""
if old in s:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("config.py 已改")
else:
    print("跳过 config.py（锚点没找到）")
