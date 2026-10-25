import json
import sys

path = r"E:\dramakit\_klein_t2i.json"
w = json.load(open(path, encoding="utf-8"))
for sg in w["definitions"]["subgraphs"]:
    for n in sg.get("nodes") or []:
        if n.get("type") == "PrimitiveStringMultiline":
            txt = (n.get("widgets_values") or [""])[0]
            print("=" * 78)
            print(f"SUBGRAPH {sg.get('name')}  node {n.get('id')}  len={len(txt)}")
            print("=" * 78)
            print(txt)
            print()
