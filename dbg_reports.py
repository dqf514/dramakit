import glob
import json
import re

for p in sorted(glob.glob(r"E:\dramakit\rounds\reports\round*.qa.json"),
                key=lambda x: int(re.search(r"round(\d+)", x).group(1))):
    n = int(re.search(r"round(\d+)", p).group(1))
    d = json.load(open(p, encoding="utf-8"))
    e = d["episodes"][0] if d["episodes"] else {}
    c = e.get("completeness") or {}
    print(f"第{n}轮 {d['verdict']}  {d['issue_count']} 个问题  "
          f"成片 {c.get('duration','-')}s / 时间线 {c.get('timeline','-')}s")
    for i in d["issues"]:
        print(f"    [{i['area']}/{i['kind']}] {i['detail'][:100]}")
