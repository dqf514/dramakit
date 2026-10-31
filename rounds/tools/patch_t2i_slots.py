"""Four reference pictures for the stills, not two.

The still of a shot is drawn with the characters' faces and the room as
its references, and the workflow had two slots: with two characters in the
frame the room was the one that got pushed out, and the room is what keeps
the shots of one scene looking like they happen in the same place.

The workflow's reference node names its slots images.image0, images.image1,
... so the slots are added the way it expects them.
"""
import json
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\comfyui\\t2i_flux3_klein_ref.json")
d = json.loads(p.read_text(encoding="utf-8"))

if "203" in d:
    print("已经扩过了")
else:
    master = d["201"]
    for nid in ("203", "204"):
        node = json.loads(json.dumps(master))
        node["inputs"]["image"] = "example.png"
        d[nid] = node
    d["130"]["inputs"]["images.image2"] = ["203", 0]
    d["130"]["inputs"]["images.image3"] = ["204", 0]
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("t2i 参考图槽位扩到 4 个（203/204）")
