"""Compare the teacher's fast and good workflows: what is inside the subgraph."""
import json
from pathlib import Path

folder = Path(r"E:\\dramakit\\rounds\\teacher_h3")


def subgraph(f):
    d = json.loads(f.read_text(encoding="utf-8"))
    defs = d.get("definitions") or {}
    out = {}
    if isinstance(defs, dict) and isinstance(defs.get("subgraphs"), list):
        for defn in defs["subgraphs"]:
            if isinstance(defn, dict):
                out[defn.get("id", "?")] = defn.get("nodes") or []
        return d, out
    for name, defn in defs.items():
        if isinstance(defn, dict):
            out[name] = defn.get("nodes") or []
        elif isinstance(defn, list):
            out[name] = defn
    return d, out


for f in sorted(folder.glob("*.json")):
    if "文生视频" not in f.name:
        continue
    d, defs = subgraph(f)
    print("=" * 72)
    print(f.name)
    for name, nodes in defs.items():
        print(f"  子图 '{name}': {len(nodes)} 节点")
        for n in nodes:
            t = str(n.get("type", ""))
            if t in ("Note", "MarkdownNote"):
                continue
            w = n.get("widgets_values")
            bits = ""
            if isinstance(w, dict):
                bits = " ".join(f"{k}={v}" for k, v in w.items()
                                if k in ("steps", "denoise", "width", "height",
                                         "length", "ref_image_size", "unet_name",
                                         "clip_name", "vae_name", "lora_name",
                                         "strength_model", "scheduler", "sampler",
                                         "seed", "noise_seed", "start_at_step",
                                         "total_steps", "end_at_step"))
            elif isinstance(w, list):
                bits = " ".join(str(x)[:26] for x in w[:10])
            print(f"    {n.get('id'):>4} {t:<30} {bits[:130]}")
