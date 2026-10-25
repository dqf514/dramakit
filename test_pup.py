"""Run the full official FLUX 3 pipeline: prompt upsampler -> diffusion."""
import json
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8188"
OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\flux3_diag")
OUT.mkdir(parents=True, exist_ok=True)
SYSTEM = Path(r"E:\dramakit\_pup_system.txt").read_text(encoding="utf-8")

SHORT = "a red apple on a wooden table"


def post(graph):
    body = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(f"{BASE}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print("提交失败:", e.read().decode("utf-8", "replace")[:800])
        raise


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
            (OUT / name).write_bytes(data)
            return str(OUT / name)
    return None


def build(prompt, width=1024, height=1024, steps=16, use_pup=True):
    g = {
        # --- prompt upsampler (official) ---
        "201": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors",
            "type": "flux3", "device": "default"}},
        "202": {"class_type": "TextGenerate", "inputs": {
            "clip": ["201", 0],
            "prompt": prompt,
            "max_length": 3584,
            "sampling_mode": "on",
            "sampling_mode.temperature": 1.0,
            "sampling_mode.top_k": 1,
            "sampling_mode.top_p": 0.95,
            "sampling_mode.min_p": 0,
            "sampling_mode.repetition_penalty": 1,
            "sampling_mode.seed": 758781618552631,
            "sampling_mode.presence_penalty": 1.5,
            "thinking": False,
            "use_default_template": True,
            "mtp": "off",
            "system_prompt": SYSTEM}},
        "203": {"class_type": "PreviewAny", "inputs": {"source": ["202", 0]}},
        # --- diffusion ---
        "101": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "flux3-image-klein-int8-convrot.safetensors",
            "weight_dtype": "default"}},
        "102": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen3vl_4b_int8_convrot.safetensors",
            "type": "flux3", "device": "default"}},
        "103": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "104": {"class_type": "CLIPTextEncode", "inputs": {
            "text": ["202", 0] if use_pup else prompt, "clip": ["102", 0]}},
        "105": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["102", 0]}},
        "106": {"class_type": "EmptyFlux2LatentImage", "inputs": {
            "width": width, "height": height, "batch_size": 1}},
        "107": {"class_type": "KSampler", "inputs": {
            "seed": 758781618552631, "steps": steps, "cfg": 1.0,
            "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0,
            "model": ["112", 0], "positive": ["104", 0], "negative": ["105", 0],
            "latent_image": ["106", 0]}},
        "108": {"class_type": "VAEDecode", "inputs": {
            "samples": ["107", 0], "vae": ["103", 0]}},
        "109": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": "diag", "images": ["108", 0]}},
        "112": {"class_type": "ModelSamplingFlux", "inputs": {
            "model": ["101", 0], "base_shift": 2.7725887, "max_shift": 2.7725887,
            "width": width, "height": height}},
    }
    return g


if __name__ == "__main__":
    t0 = time.time()
    g = build(SHORT)
    pid = post(g)["prompt_id"]
    h = wait(pid)
    p = save(h, "J_官方全链路.png")
    print(f"耗时 {time.time()-t0:.0f}s -> {p}")
    # the upsampler's caption is the text output of PreviewAny
    for nid, out in (h.get("outputs") or {}).items():
        for o in out.get("text", []) if isinstance(out, dict) else []:
            print("--- 扩写后的提示词 ---")
            print(str(o)[:1200])
