"""Isolate the FLUX 3 failure: VAE round-trip vs conditioning vs sampling."""
import json
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8188"
OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\flux3_diag")
OUT.mkdir(parents=True, exist_ok=True)


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
            src = (f"{BASE}/view?filename={img['filename']}"
                   f"&subfolder={img.get('subfolder','')}&type={img.get('type','output')}")
            with urllib.request.urlopen(src, timeout=60) as r:
                data = r.read()
            (OUT / name).write_bytes(data)
            return str(OUT / name)
    return None


# ---- 1) VAE round trip: encode the sample image, decode it back ----
g = {
    "1": {"class_type": "LoadImage", "inputs": {"image": "sample.png"}},
    "2": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
    "3": {"class_type": "VAEEncode", "inputs": {"pixels": ["1", 0], "vae": ["2", 0]}},
    "4": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["2", 0]}},
    "5": {"class_type": "SaveImage", "inputs": {
        "filename_prefix": "diag/vae_roundtrip", "images": ["4", 0]}},
}
p = save(wait(post(g)["prompt_id"]), "G_VAE往返.png")
print("[VAE round-trip] ->", p)

# ---- 2) no prompt at all (pure noise -> should be colored noise) ----
g = {
    "101": {"class_type": "UNETLoader", "inputs": {
        "unet_name": "flux3-image-klein-int8-convrot.safetensors",
        "weight_dtype": "default"}},
    "102": {"class_type": "CLIPLoader", "inputs": {
        "clip_name": "qwen3vl_4b_int8_convrot.safetensors",
        "type": "flux3", "device": "default"}},
    "103": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
    "104": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "a red apple on a wooden table", "clip": ["102", 0]}},
    "106": {"class_type": "EmptyFlux2LatentImage", "inputs": {
        "width": 1024, "height": 1024, "batch_size": 1}},
    "107": {"class_type": "KSampler", "inputs": {
        "seed": 7, "steps": 16, "cfg": 1.0, "sampler_name": "euler",
        "scheduler": "simple", "denoise": 1.0,
        "model": ["101", 0], "positive": ["104", 0], "negative": ["104", 0],
        "latent_image": ["106", 0]}},
    "108": {"class_type": "VAEDecode", "inputs": {
        "samples": ["107", 0], "vae": ["103", 0]}},
    "109": {"class_type": "SaveImage", "inputs": {
        "filename_prefix": "diag/simple", "images": ["108", 0]}},
}
p = save(wait(post(g)["prompt_id"]), "H_简单提示词.png")
print("[simple prompt, no ModelSamplingFlux] ->", p)

# ---- 3) fp8 weight dtype variant ----
g2 = json.loads(json.dumps(g))
g2["101"]["inputs"]["weight_dtype"] = "fp8_e4m3fn"
g2["109"]["inputs"]["filename_prefix"] = "diag/fp8"
p = save(wait(post(g2)["prompt_id"]), "I_weight_dtype_fp8.png")
print("[weight_dtype=fp8_e4m3fn] ->", p)
