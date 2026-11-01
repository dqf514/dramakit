"""What encoding is the novel in now, and does it have chapters?

The file changed size between two reads, and decoding it as GBK produced
the classic sign of UTF-8-read-as-GBK mojibake - so it may have been
re-saved since. This identifies the encoding properly rather than
assuming, then looks for whatever chapter headings the book actually uses.
"""
import re
from pathlib import Path

SRC = Path(r"E:\dramakit\projects\九天灭魔传\source\九天灭魔传.txt")
raw = SRC.read_bytes()

print("字节数:", len(raw))
print("BOM:", raw[:3] == b"\xef\xbb\xbf")

for enc in ("utf-8", "gb18030"):
    try:
        t = raw.decode(enc)
        han = sum(1 for c in t if "一" <= c <= "鿿")
        print(f"{enc}: 解码成功 {len(t)} 字, 汉字 {han} 个 ({han*100//max(len(t),1)}%)")
    except UnicodeDecodeError as e:
        print(f"{enc}: 失败 -> {str(e)[:60]}")

# trust whichever worked
for enc in ("utf-8", "gb18030"):
    try:
        t = raw.decode(enc)
        break
    except UnicodeDecodeError:
        continue

print()
print("=== 开头 400 字 ===")
print(t[:400])
print()

# what headings does this book actually use?
print("=== 标题样式探测 ===")
for name, pat in [
    ("第X章", r"^第[0-9一二三四五六七八九十百千]+章.*$"),
    ("第X节", r"^第[0-9一二三四五六七八九十百千]+节.*$"),
    ("【第X章】", r"^【.*?】.*$"),
    ("数字.标题", r"^\d{1,4}[.、．].{2,30}$"),
    ("纯数字行", r"^\d{1,4}$"),
]:
    hits = re.findall(pat, t, re.M)
    print(f"  {name:<12} {len(hits):>4} 个  {hits[:3]}")

# chapter markers the book announces
m = re.search(r"更新到第[^\r\n】]*", t)
print()
print("状态行:", m.group(0) if m else "(无)")
