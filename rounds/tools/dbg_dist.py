"""How many jobs went to each node in the last run?"""
import re
import sys
from pathlib import Path

log = Path(r"E:\\dramakit\\projects\\轮次09_09\\logs\\pipeline.log")
text = log.read_text(encoding="utf-8", errors="replace").splitlines()
# the last reset starts the current run
start = 0
for i, line in enumerate(text):
    if "重置" in line:
        start = i
counts: dict[str, int] = {}
for line in text[start:]:
    m = re.search(r"i2v 已提交.*@(http://\S+)", line)
    if m:
        url = m.group(1)
        counts[url] = counts.get(url, 0) + 1
print("这一轮的视频任务分布：")
for url, n in sorted(counts.items(), key=lambda kv: -kv[1]):
    print(f"  {n:>3}  {url}")
print("总计", sum(counts.values()))
