import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8-sig"))
for f in d.get("siblings", []):
    n = f.get("rfilename", "")
    if any(k in n for k in sys.argv[2:]):
        print(f"{(f.get('size') or 0)/1e9:7.2f} GB  {n}")
