"""Put the broken characters right.

Some of the text in the prompt files came back from a write with half
a character in it: utf-8 that does not decode shows up as the
replacement character, and the prompt would have gone out with it in.

The damage is found by where the replacement characters are, and what
they should say comes from the sentence around them.
"""
import pathlib
import re

ROOT = pathlib.Path(r"E:\dramakit")
R = "�"

# file -> list of (the text before the damage, the text after it, what
# the damage should say)
FIXES = {
    "dramakit/skills/film.py": [
        ("只输出JSON", '"""', "。"),
        ("**一、一", "= 一个片段", "行"),
        ("不是", "个镜头**", "一"),
    ],
    "dramakit/prompts/templates.py": [
        ("**每一拍都要被某一段拍", "*，漏掉一拍就是漏掉一", "到"),
        ("漏掉一拍就是漏掉一", "画面", "个"),
    ],
}

for rel, fixes in FIXES.items():
    p = ROOT / rel
    raw = p.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8", errors="replace")
    before = text.count(R)
    for head, tail, what in fixes:
        pattern = re.escape(head) + R + "+" + re.escape(tail)
        m = re.search(pattern, text)
        if not m:
            print("  !! not found: %s...%s (%s)" % (head[:14], tail[:14], rel))
            continue
        text = text[:m.start()] + head + what + tail + text[m.end():]
    after = text.count(R)
    if crlf:
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    p.write_bytes(text.encode("utf-8"))
    print("  %-40s bad %d -> %d" % (rel, before, after))
