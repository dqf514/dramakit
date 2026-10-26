import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

p = Path(r"E:\dramakit\projects\测试短剧\subs\ep_001.ass")
lines = p.read_text(encoding="utf-8").splitlines()
mx = 0
n = 0
over = []
for l in lines:
    if not l.startswith("Dialogue:"):
        continue
    n += 1
    txt = l.split(",", 9)[-1]
    txt = re.sub(r"\{[^}]*\}", "", txt).replace("\\N", " ").replace("\\n", " ").strip()
    mx = max(mx, len(txt))
    if len(txt) > 18:
        over.append((len(txt), txt))
print("字幕条数", n, "最长可见字符", mx)
print("超过 18 字的：", len(over))
for t in over[:6]:
    print("   ", t[0], t[1][:50])
print()
for l in lines:
    if l.startswith("Style: Narration") or l.startswith("Style: Dialogue") \
            or l.startswith("Style: Caption"):
        print(l[:160])
