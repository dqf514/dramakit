"""Build the reference-to-video workflow with a reference audio slot.

The still goes in as the picture reference and the recorded line goes in as
the voice-timbre reference, so H3 says our words in our voice while it draws
the mouth - picture, voice and sound effect in one pass.
"""
import json
from pathlib import Path

ROOT = Path(r"E:\dramakit\config\comfyui")
SRC = ROOT / "i2v_minimax_h3.json"
DST = ROOT / "i2v_minimax_h3_ref2v_audio.json"

MODEL = "MiniMax_H3_Ref2VA_pruned_nvfp4.safetensors"
LORA = "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors"

graph = json.load(open(SRC, encoding="utf-8"))

for nid, node in graph.items():
    if not isinstance(node, dict):
        continue
    ct = node.get("class_type", "")
    if ct == "UNETLoader":
        node["inputs"]["unet_name"] = MODEL
    if ct == "LoraLoaderModelOnly":
        node["inputs"]["lora_name"] = LORA
    if ct == "MiniMaxH3ImageToVideo":
        ins = node["inputs"]
        image_node = ins.get("first_frame", ["1", 0])[0]
        node["class_type"] = "MiniMaxH3ReferenceToVideo"
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
            "ref_audios": {"ref_audio_0": ["900", 0]},
        }

# the node that loads the reference voice
graph["900"] = {
    "class_type": "LoadAudio",
    "inputs": {"audio": "placeholder.mp3", "upload": "audio"},
}

json.dump(graph, open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"已写出 {DST}")
for nid, node in graph.items():
    if isinstance(node, dict) and node.get("class_type", "").startswith(
            ("MiniMaxH3", "LoadAudio")):
        print(f"  {nid}: {node['class_type']}")
