"""What does the server say about the nodes we need for the audio path?"""
import json
import subprocess
import sys

out = subprocess.run(["curl.exe", "-s", "--max-time", "40",
                      "http://127.0.0.1:8188/object_info"],
                     capture_output=True, text=True, errors="replace").stdout
info = json.loads(out)
for name in sys.argv[1:]:
    node = info.get(name)
    if not node:
        print(f"{name}: 没有这个节点")
        continue
    ins = node.get("input", {})
    print(f"=== {name}: {node.get('display_name','')}")
    for section in ("required", "optional"):
        for k, v in (ins.get(section) or {}).items():
            t = v[0] if isinstance(v, list) and v else v
            opts = v[1] if isinstance(v, list) and len(v) > 1 else ""
            print(f"   [{section}] {k}: {t} {opts if isinstance(opts, str) else ''}")
    print()
