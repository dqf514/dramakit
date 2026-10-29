"""Give the video the references it needs.

The video used to be made from the first frame alone, so the model had
one picture to guess the person and the room from - and it guessed
differently every time. Now every video job carries the character's three
views, the room and the frame it continues from.

And a job without that set is not started at all: drawing a clip without
the references wastes the card and gives a face that belongs to nobody.
"""
from pathlib import Path

# 1) the workflow: four more reference slots
p = Path(r"E:\\dramakit\\config\\comfyui\\i2v_minimax_h3_ref2v_audio.json")
g = json_load = None
import json as _json
g = _json.loads(p.read_text(encoding="utf-8"))

for nid, node in list(g.items()):
    if not isinstance(node, dict):
        continue
    if node.get("class_type") != "MiniMaxH3ReferenceToVideo":
        continue
    refs = node["inputs"].setdefault("ref_images", {})
    # 0 is the frame the shot continues from; 1..4 are the sheets and the room
    for i in range(1, 5):
        slot = f"ref_image_{i}"
        load_id = str(900 + i)
        refs[slot] = [load_id, 0]
        g[load_id] = {
            "class_type": "LoadImage",
            "inputs": {"image": "placeholder.png", "upload": "image"},
        }
p.write_text(_json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
print("工作流: 参考图槽位扩到 5 个")

# 2) the client: fill the slots with the pictures it was given
p = Path(r"E:\\dramakit\\dramakit\\providers\\comfyui.py")
s = p.read_text(encoding="utf-8")
old = """        # the voice reference: the recording of the line goes in as the
        # timbre the character speaks with
        ref_audio = extra.get("ref_audio_path")"""
new = """        # the pictures: the character sheets, the room and the frame the
        # shot continues from. The workflow says which load node is which
        # slot, so the order is the one both sides agreed on.
        pictures = list(extra.get("ref_pictures") or [])
        if pictures:
            slots: list[tuple[str, str]] = []
            for nid, node in graph.items():
                if not isinstance(node, dict):
                    continue
                if "ReferenceToVideo" in str(node.get("class_type", "")):
                    for slot, link in sorted(
                            (node.get("inputs", {}).get("ref_images") or {}).items()):
                        if isinstance(link, list) and link:
                            slots.append((str(link[0]), slot))
                    break
            for (load_id, _slot), path in zip(slots, pictures):
                if load_id not in graph or not Path(path).exists():
                    continue
                graph[load_id].setdefault("inputs", {})["image"] = self.upload_image(path)
        # the voice reference: the recording of the line goes in as the
        # timbre the character speaks with
        ref_audio = extra.get("ref_audio_path")"""
assert old in s, "客户端锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("comfyui.py: 按槽上传参考图")
