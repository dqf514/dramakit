"""A small GBK novel, to prove the upload survives its encoding.

The bug was that the browser decoded every upload as UTF-8 and swapped the
unmatched bytes for U+FFFD, so a GBK book reached the server already
mangled and no chapter heading could be found. This writes a book in GBK
with real 第X章 headings, so the upload can be tested against the thing
that broke it.
"""
from pathlib import Path

OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\gbk_novel.txt")

chapters = [
    ("第一章 穿越", "夜色深沉，少年站在山巅，望着脚下的城池。他从未想过，一次坠落会让他来到这个世界。"),
    ("第二章 觉醒", "体内忽然涌出一股暖流，经脉寸寸打通。他睁开眼，看见掌心浮起一枚古老的印记。"),
    ("第三章 风起", "山下的追兵已经赶到，火把连成一条长龙。他转身，向着更深的山林走去。"),
    ("第四章 故人", "客栈里那个背影，分明是故人的模样。他握紧了刀，缓步上前。"),
    ("第五章 决裂", "杯酒落地，恩义两断。从今往后，你我陌路。他说完，推门而出。"),
]

parts = ["九天灭魔传", ""]
for title, body in chapters:
    parts.append(title)
    parts.append(body)
    parts.append("")
text = "\n".join(parts)

OUT.write_bytes(text.encode("gbk"))
print("GBK 测试小说:", OUT)
print("大小:", OUT.stat().st_size, "字节")
print("章节数:", len(chapters))

# prove it really is GBK and really is undecodable as UTF-8
raw = OUT.read_bytes()
try:
    raw.decode("utf-8")
    print("警告: 这个文件居然能用 UTF-8 解码，测不出问题")
except UnicodeDecodeError as e:
    print("确认: UTF-8 解码失败 ->", str(e)[:70])
print("GB18030 解码:", len(raw.decode("gb18030")), "字")
