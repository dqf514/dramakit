"""Can the mangled novel be read at all?

The upload decoded a GBK book as UTF-8 and swapped what it could not read
for U+FFFD, then wrote that back - so the original bytes are gone. But the
substitution was byte-by-byte, and GBK is two bytes per character, so some
characters may have survived as their original bytes while only others were
destroyed. If enough survived, the chapter headings are still findable and
the project does not have to be re-imported.
"""
from pathlib import Path

SRC = Path(r"E:\dramakit\projects\九天灭魔传\source\九天灭魔传.txt")

raw = SRC.read_bytes()
print("字节数:", len(raw))
print("U+FFFD 序列 (EF BF BD) 出现:", raw.count(b"\xef\xbf\xbd"), "次")
print()

# decode leniently: the surviving GBK bytes become characters, the
# destroyed ones become U+FFFD - which is at least readable where it can be
t = raw.decode("gb18030", errors="replace")
ok = sum(1 for c in t if c.isalnum() or "一" <= c <= "鿿")
bad = t.count("\ufffd")
print("gb18030 宽松解码:", len(t), "字")
print("  可读字符:", ok, f"({ok*100//max(len(t),1)}%)")
print("  损坏字符:", bad, f"({bad*100//max(len(t),1)}%)")
print()
print("开头 300 字:")
print(repr(t[:300]))
print()

# do any chapter headings survive?
import re
pat = re.compile(r"^第[0-9一二三四五六七八九十百千]+章", re.M)
hits = pat.findall(t)
print("能认出的章节标题:", len(hits), "个 ->", hits[:12])
