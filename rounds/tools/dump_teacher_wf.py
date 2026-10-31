"""What is in the teacher's H3 workflows?"""
import json
import sys
from pathlib import Path

folder = Path(r"E:\\dramakit\\rounds\\teacher_h3")
WATCH = {
    "KSampler", "KSamplerAdvanced", "SamplerCustomAdvanced", "LatentUpscale",
    "BasicScheduler", "RandomNoise", "SamplerCustom", "BasicGuider", "CFGGuider",
    "VAEDecode", "SaveVideo", "CreateVideo", "CLIPLoader", "UNETLoader",
    "VAELoader", "LoadImage", "LoraLoader", "LoraLoaderModelOnly",
    "LatentFromBatch", "RepeatLatentBatch", "ImageScale", "LatentUpscale",
    "MiniMaxH3ReferenceToVideo", "MiniMaxH3TextToVideo",
    "MiniMaxH3FirstLastFrameToVideo", "ModelSamplingFlux", "EmptyLatentImage",
    "LatentComposite", "ImageBatch", "RepeatImageBatch", "Note",
}


def widgets(n):
    w = n.get("widgets_values")
    return w if isinstance(w, list) else []


for f in sorted(folder.glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    nodes = d.get("nodes") or []
    print("=" * 72)
    print(f.name, f"({len(nodes)} 节点)")
    for n in nodes:
        t = str(n.get("type", ""))
        if t not in WATCH:
            continue
        w = widgets(n)
        bits = []
        if t == "KSampler":
            bits = [f"steps={w[0]}", f"cfg={w[1]}", f"sampler={w[2]}",
                    f"sched={w[3]}", f"denoise={w[4]}"]
        elif t == "BasicScheduler":
            bits = [f"steps={w[1] if len(w) > 1 else '?'}",
                    f"sched={w[2] if len(w) > 2 else '?'}"]
        elif t == "UNETLoader":
            bits = [f"unet={w[0]}"]
        elif t == "LoraLoaderModelOnly":
            bits = [f"lora={w[0]}", f"strength={w[1] if len(w) > 1 else '?'}"]
        elif t == "LatentUpscale":
            bits = [f"method={w[0] if w else '?'}"]
        elif t == "CLIPLoader":
            bits = [f"clip={w[0] if w else '?'}"]
        elif t == "VAELoader":
            bits = [f"vae={w[0] if w else '?'}"]
        elif t in ("MiniMaxH3ReferenceToVideo", "MiniMaxH3TextToVideo",
                   "MiniMaxH3FirstLastFrameToVideo"):
            wi = n.get("widgets_values")
            if isinstance(wi, dict):
                bits = [f"{k}={v}" for k, v in wi.items()
                        if k in ("width", "height", "length", "ref_image_size")]
            elif isinstance(wi, list):
                bits = [str(x)[:40] for x in wi[:8]]
        elif t == "Note":
            bits = [str(n.get("properties", {}).get("text", ""))[:60]]
        print(f"  {n.get('id'):>5} {t:<28} {'  '.join(str(b) for b in bits)}")
