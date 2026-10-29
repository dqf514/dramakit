"""Build the reference-to-video workflow from the image-to-video one.

MiniMax publishes two open-weight H3 transformers: fl2va (first/last frame
to video) and ref2va (reference to video). The reference one keeps the
reference in the attention at every sampling step, so the face does not
drift away from the picture it came from.

Same graph, two changes: the transformer file and the conditioning node.
"""
import json
from pathlib import Path

ROOT = Path(r"E:\dramakit\config\comfyui")
SRC = ROOT / "i2v_minimax_h3.json"
DST = ROOT / "i2v_minimax_h3_ref2v.json"

graph = json.load(open(SRC, encoding="utf-8"))

# 1) the transformer
for nid, node in graph.items():
    if not isinstance(node, dict):
        continue
    ct = node.get("class_type", "")
    if ct == "UNETLoader":
        node["inputs"]["unet_name"] = "minimax_h3_ref2va_pruned_w6a8.safetensors"
    if ct == "LoraLoaderModelOnly":
        node["inputs"]["lora_name"] = (
            "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors")

# 2) the conditioning node: first frame -> reference image
for nid, node in graph.items():
    if not isinstance(node, dict):
        continue
    if node.get("class_type") != "MiniMaxH3ImageToVideo":
        continue
    ins = node["inputs"]
    image_node = ins.get("first_frame", ["1", 0])[0]
    node["class_type"] = "MiniMaxH3ReferenceToVideo"
    node.pop("_meta", None)
    node["inputs"] = {
        "clip": ins["clip"],
        "vae": ins["vae"],
        "audio_vae": ins.get("audio_vae", ["24", 0]),
        "prompt": ins.get("prompt", "placeholder"),
        "width": ins.get("width", 768),
        "height": ins.get("height", 1344),
        "length": ins.get("length", 124),
        "ref_image_size": "match",
        "ref_images": {"ref_image_0": [image_node, 0]},
    }

json.dump(graph, open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"已写出 {DST}")
for nid, node in graph.items():
    if isinstance(node, dict) and node.get("class_type", "").startswith("MiniMaxH3"):
        print(f"  {nid}: {node['class_type']}")
        print(f"     {json.dumps(node['inputs'], ensure_ascii=False)[:220]}")
