"""Diagnose the FLUX 3 t2i output: try variants of the graph."""
import copy
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8188"
OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\flux3_diag")
OUT.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "Full-color outdoor photograph, medium shot, a woman in her early thirties "
    "stands in the doorway of a cramped old apartment at dusk. She has fair skin, "
    "straight shoulder-length black hair, and wears a pale grey wool coat. "
    "Warm tungsten light falls across her face, cool dusk light fills the doorway."
)


def post(graph):
    body = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(f"{BASE}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def wait(pid, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with urllib.request.urlopen(f"{BASE}/history/{pid}", timeout=30) as r:
            h = json.loads(r.read())
        if pid in h:
            return h[pid]
        time.sleep(1)
    return {}


def save(h, name):
    for out in h.get("outputs", {}).values():
        for img in out.get("images", []):
            src = f"{BASE}/view?filename={img['filename']}&subfolder={img.get('subfolder','')}&type={img.get('type','output')}"
            with urllib.request.urlopen(src, timeout=60) as r:
                data = r.read()
            p = OUT / name
            p.write_bytes(data)
            return str(p)
    return None


def graph(**over):
    g = {
        "101": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "flux3-image-klein-int8-convrot.safetensors",
            "weight_dtype": "default"}},
        "102": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen3vl_4b_int8_convrot.safetensors",
            "type": "flux3", "device": "default"}},
        "103": {"class_type": "VAELoader", "inputs": {
            "vae_name": "flux2-vae.safetensors"}},
        "104": {"class_type": "CLIPTextEncode", "inputs": {
            "text": PROMPT, "clip": ["102", 0]}},
        "105": {"class_type": "CLIPTextEncode", "inputs": {
            "text": "", "clip": ["102", 0]}},
        "106": {"class_type": "EmptyFlux2LatentImage", "inputs": {
            "width": 1344, "height": 768, "batch_size": 1}},
        "107": {"class_type": "KSampler", "inputs": {
            "seed": 20261025, "steps": 16, "cfg": 1.0, "sampler_name": "euler",
            "scheduler": "simple", "denoise": 1.0,
            "model": ["112", 0], "positive": ["104", 0], "negative": ["105", 0],
            "latent_image": ["106", 0]}},
        "108": {"class_type": "VAEDecode", "inputs": {
            "samples": ["107", 0], "vae": ["103", 0]}},
        "109": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": "diag", "images": ["108", 0]}},
        "112": {"class_type": "ModelSamplingFlux", "inputs": {
            "model": ["101", 0], "base_shift": 2.7725887, "max_shift": 2.7725887,
            "width": 1344, "height": 768}},
    }
    for k, v in over.items():
        if k == "drop":
            for nid in v:
                g.pop(nid, None)
        elif k == "set":
            nid, fields = v
            g[nid]["inputs"].update(fields)
        elif k == "relink":
            nid, field, src = v
            g[nid]["inputs"][field] = src
    return g


CASES = {
    "A_官方原样_1344x768": graph(),
    "B_去掉ModelSamplingFlux": graph(relink=("107", "model", ["101", 0])),
    "C_1024x1024": graph(set=("106", {"width": 1024, "height": 1024})),
    "D_去掉负向节点": graph(
        drop=["105"],
        set=("107", {"negative": ["104", 0]})),
    "E_cfg3": graph(set=("107", {"cfg": 3.0})),
    "F_24步": graph(set=("107", {"steps": 24})),
}

for name, g in CASES.items():
    try:
        pid = post(g)["prompt_id"]
        h = wait(pid)
        p = save(h, f"{name}.png")
        print(f"[{name}] -> {p}")
    except Exception as e:  # noqa: BLE001
        body = ""
        if hasattr(e, "read"):
            body = e.read().decode("utf-8", "replace")[:300]
        print(f"[{name}] ERR {e} {body}")
