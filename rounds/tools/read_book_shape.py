"""The shape of the book.

The chapters, how long each one is, and how the story ends - because
an adaptation has to know where the road goes before it lays a stone.
"""
import pathlib
import re
import sys

PROJ = pathlib.Path(r"E:\dramakit\projects") / sys.argv[1] if len(sys.argv) > 1 else None
if PROJ is None:
    cands = [d for d in pathlib.Path(r"E:\dramakit\projects").iterdir()
             if d.is_dir() and (d / "source" / "cleaned.txt").exists()]
    cands.sort(key=lambda d: (d / "source" / "cleaned.txt").stat().st_mtime,
               reverse=True)
    PROJ = cands[0]

text = (PROJ / "source" / "cleaned.txt").read_text(encoding="utf-8", errors="replace")
print("  正文 %d 字" % len(text))

# the chapter marks: a line that is only a number and a title
marks = list(re.finditer(r"^第[^\n]{1,12}章[^\n]*$", text, re.M))
if not marks:
    marks = list(re.finditer(r"^\s*第[一二三四五六七八九十百千零〇\d]+[^\n]{0,14}$",
                              text, re.M))
print("  找到 %d 章" % len(marks))
if marks:
    print("\n=== 章目 ===")
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        words = len(re.sub(r"\s", "", body))
        print("  %-34s %5d 字" % (m.group().strip()[:32], words))
    print("\n=== 最后一章 ===")
    print(text[marks[-1].start():marks[-1].start() + 2500])
