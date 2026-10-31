"""The sizes: 768p everywhere, by line, not by matching a block.

The comments in the config change as the settings change, so matching on a
comment is a way to miss.  These are the lines that carry the numbers.
"""
from pathlib import Path
import re

c = Path(r"E:\\dramakit\\config\\default.yaml")
s = c.read_text(encoding="utf-8")


def set_line(key: str, value: str, note: str) -> None:
    global s
    pat = re.compile(rf"^({re.escape(key)}:\s*)\S+.*$", re.M)
    m = pat.search(s)
    assert m, f"配置里没有 {key}"
    s = pat.sub(lambda _m: f"{_m.group(1)}{value}".ljust(44) + f"# {note}", s, count=1)


set_line("  width", "1344", "出图分辨率（H3 原生 768p，16:9）")
set_line("  height", "768", "出图分辨率")
set_line("  video_width", "1344", "视频分辨率（H3 原生 768p，16:9）")
set_line("  video_height", "768", "视频分辨率")
set_line("  ref_width", "1344", "面部满屏照：跟出图同尺寸")
set_line("  ref_height", "768", "面部满屏照")
set_line("  ref_body_width", "768", "全身视图用竖幅：宽幅里人太小、灰底太多")
set_line("  ref_body_height", "1344", "全身视图")

# compose.width / compose.height are further down and share the key names
part = s.split("\ncompose:\n", 1)
assert len(part) == 2, "找不到 compose 段"
head, tail = part
tail = re.sub(r"^(\s*width:\s*)\S+.*$", lambda m: m.group(1) + "1344".ljust(29) + "# 16:9 横屏 768p 成片",
              tail, count=1, flags=re.M)
tail = re.sub(r"^(\s*height:\s*)\S+.*$", lambda m: m.group(1) + "768".ljust(29) + "# 16:9 横屏 768p 成片",
              tail, count=1, flags=re.M)
s = head + "\ncompose:\n" + tail

c.write_text(s, encoding="utf-8")
print("config/default.yaml: 全线 1344x768（768p）")
