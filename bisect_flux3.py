"""Bisect the FLUX 3 failure: model variant x shift x upsampler.

Scores each output objectively (Laplacian variance = sharpness, saturation,
entropy) instead of eyeballing every frame.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8188"
OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\flux3_bisect")
OUT.mkdir(parents=True, exist_ok=True)
SYSTEM = Path(r"E:\dramakit\_pup_system.txt").read_text(encoding="utf-8")

SHORT = "a red apple on a wooden table"


def post(graph):
    body = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(f"{BASE}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def wait(pid, timeout=900):
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
            p = OUT / name
            p.write_bytes(data)
            return p
    return None


def score(p):
    """Sharpness (Laplacian variance), saturation, entropy via ffmpeg."""
    if not p:
        return {}
    cmd = ["ffmpeg", "-hide_banner", "-i", str(p), "-vf",
           "signalstats,metadata=print:file=-", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    txt = r.stderr + r.stdout
    import re
    def mean(key):
        vals = [float(v) for v in re.findall(rf"signalstats\.{key}=(-?[\d.]+)", txt)]
        return sum(vals) / len(vals) if vals else 0.0
    sharp = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(p), "-vf",
         "convolution=0 1 0 1 -4 1 0 1 0", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace")
    import re as _re
    m = _re.findall(r"lavfi\.convolution\.MAX=([\d.]+)", sharp.stderr)
    return {"luma": round(mean("YAVG"), 1), "sat": round(mean("SATAVG"), 1),
            "contrast": round(mean("YHIGH") - mean("YLOW"), 1),
            "sharp_max": round(float(m[-1]), 1) if m else 0.0}


def build(unet, clip, use_pup, shift, steps=16, cfg=1.0, w=1024, h=1024,
          sampler="euler", scheduler="simple", with_msf=True):
    g = {
        "101": {"class_type": "UNETLoader", "inputs": {
            "unet_name": unet, "weight_dtype": "default"}},
        "102": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": clip, "type": "flux3", "device": "default"}},
        "103": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "104": {"class_type": "CLIPTextEncode", "inputs": {
            "text": ["202", 0] if use_pup else SHORT, "clip": ["102", 0]}},
        "105": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["102", 0]}},
        "106": {"class_type": "EmptyFlux2LatentImage", "inputs": {
            "width": w, "height": h, "batch_size": 1}},
        "107": {"class_type": "KSampler", "inputs": {
            "seed": 758781618552631, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler, "denoise": 1.0,
            "model": ["112", 0] if with_msf else ["101", 0],
            "positive": ["104", 0], "negative": ["105", 0],
            "latent_image": ["106", 0]}},
        "108": {"class_type": "VAEDecode", "inputs": {
            "samples": ["107", 0], "vae": ["103", 0]}},
        "109": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": "bisect", "images": ["108", 0]}},
    }
    if use_pup:
        g["201"] = {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors",
            "type": "flux3", "device": "default"}}
        g["202"] = {"class_type": "TextGenerate", "inputs": {
            "clip": ["201", 0], "prompt": SHORT, "max_length": 3584,
            "sampling_mode": "on",
            "sampling_mode.temperature": 1.0, "sampling_mode.top_k": 1,
            "sampling_mode.top_p": 0.95, "sampling_mode.min_p": 0,
            "sampling_mode.repetition_penalty": 1,
            "sampling_mode.seed": 758781618552631,
            "sampling_mode.presence_penalty": 1.5,
            "thinking": False, "use_default_template": True, "mtp": "off",
            "system_prompt": SYSTEM}}
    if with_msf:
        g["112"] = {"class_type": "ModelSamplingFlux", "inputs": {
            "model": ["101", 0], "base_shift": shift, "max_shift": shift,
            "width": w, "height": h}}
    return g


INT8 = "flux3-image-klein-int8-convrot.safetensors"
CLIP_INT8 = "qwen3vl_4b_int8_convrot.safetensors"
CLIP_BF16 = "qwen3vl_4b_bf16.safetensors"
BF16 = "flux3-image-klein-bf16.safetensors"
NVFP4 = "flux3-image-klein-nvfp4.safetensors"
BASE_INT8 = "flux3-image-klein-base-int8-convrot.safetensors"

CASES = [
    ("1_int8_shift2.77", INT8, CLIP_INT8, False, 2.7725887, 16, 1.0),
    ("2_int8_shift1.93", INT8, CLIP_INT8, False, 1.93586, 16, 1.0),
    ("3_int8_noshift", INT8, CLIP_INT8, False, 2.7725887, 16, 1.0),
]

if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    for name, unet, clip, use_pup, shift, steps, cfg in CASES:
        if only and not name.startswith(only):
            continue
        with_msf = "noshift" not in name
        try:
            t0 = time.time()
            g = build(unet, clip, use_pup, shift, steps, cfg, with_msf=with_msf)
            pid = post(g)["prompt_id"]
            p = save(wait(pid), f"{name}.png")
            print(f"[{name}] {time.time()-t0:.0f}s {score(p)}")
        except Exception as e:  # noqa: BLE001
            body = ""
            if hasattr(e, "read"):
                body = e.read().decode("utf-8", "replace")[:300]
            print(f"[{name}] ERR {e} {body}")
