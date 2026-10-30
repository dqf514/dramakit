"""What does the H3 ref2va workflow actually output?"""
import json
from pathlib import Path

p = Path(r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v_audio.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("top keys:", list(d.keys()))
for k, v in d.items():
    if isinstance(v, dict) and "nodes" in v:
        print("nodes:", len(v["nodes"]))
        for n in v["nodes"]:
            print(f"  {n.get('id'):>5}  {n.get('type'):<34} {str(n.get('title',''))[:44]}")
    elif isinstance(v, dict):
        print(f"--- {k} ---")
        for kk, vv in v.items():
            print("   ", kk, "=", str(vv)[:150])
