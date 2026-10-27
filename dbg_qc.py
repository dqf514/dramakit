import json
from pathlib import Path

p = Path(r"E:\dramakit\projects\轮次09_09\qc\ep_001.json")
d = json.load(open(p, encoding="utf-8"))
print(json.dumps(d, ensure_ascii=False, indent=2)[:1200])
