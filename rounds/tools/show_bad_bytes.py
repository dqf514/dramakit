"""Show the broken bytes, so they can be put right.

A character that is half a character is not a character - it is three
bytes that decode to nothing.  The replacement character is where the
decoder gave up, and the bytes around it are what has to be fixed.
"""
import pathlib

ROOT = pathlib.Path(r"E:\dramakit")


def show(rel):
    p = ROOT / rel
    raw = p.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    print("=== %s ===" % rel)
    at = 0
    while True:
        i = text.find("�", at)
        if i < 0:
            break
        # the byte offset of the same place in the original
        b = len(text[:i].encode("utf-8", errors="replace"))
        print("  坏字符在第 %d 行，字节 %d 附近" % (text[:i].count("\n") + 1, b))
        print("    原文：%r" % text[max(0, i - 40):i + 40])
        print("    字节：%r" % raw[max(0, b - 20):b + 20])
        at = i + 1


for rel in ("dramakit/prompts/templates.py", "dramakit/skills/film.py"):
    show(rel)
