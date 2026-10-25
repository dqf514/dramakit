"""Ask ComfyUI what API shape ReferenceMultiLatent's dynamic inputs expect."""
import json
import urllib.request

BASE = "http://127.0.0.1:8188"


def post(graph, label):
    body = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(f"{BASE}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        print(f"[{label}] OK -> {data.get('prompt_id')}")
        return True
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(raw).get("error", {}).get("message", raw)
        except Exception:
            msg = raw
        print(f"[{label}] {e.code}: {msg[:600]}")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"[{label}] ERR {e}")
        return False


BASE_GRAPH = {
    "101": {"class_type": "UNETLoader", "inputs": {
        "unet_name": "flux3-image-klein-int8-convrot.safetensors", "weight_dtype": "default"}},
    "102": {"class_type": "CLIPLoader", "inputs": {
        "clip_name": "qwen3vl_4b_int8_convrot.safetensors", "type": "flux3", "device": "default"}},
    "103": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
    "104": {"class_type": "CLIPTextEncode", "inputs": {"text": "x", "clip": ["102", 0]}},
    "105": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["102", 0]}},
    "201": {"class_type": "LoadImage", "inputs": {"image": "example.png"}},
    # cheap output so the graph validates but nothing heavy executes:
    # ReferenceMultiLatent is not an ancestor of this node, so it never runs.
    "109": {"class_type": "SaveImage", "inputs": {
        "images": ["201", 0], "filename_prefix": "probe"}},
}

shapes = {
    "resolution=str": "resize",
    "resolution=dict-key": {"key": "resize"},
    "resolution=dict-options": {"options": [{"key": "resize", "inputs": {}}]},
    "resolution=dict-both": {"key": "resize", "options": [
        {"key": "keep resolution", "inputs": {}},
        {"key": "resize", "inputs": {"megapixels": 1.0}}]},
}
for label, val in shapes.items():
    g = json.loads(json.dumps(BASE_GRAPH))
    g["130"] = {"class_type": "ReferenceMultiLatent", "inputs": {
        "positive": ["104", 0], "negative": ["105", 0], "vae": ["103", 0],
        "resolution": val, "images.image0": ["201", 0]}}
    if post(g, label):
        break

