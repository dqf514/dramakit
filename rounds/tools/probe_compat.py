"""Does the new workflow use the same node ids the card's overrides name?

The remote card replaces three of the workflow's models with int8 weights
that its architecture can actually run, and it names them by node id: 13
for the text encoder, 6 for the sampler's model, 11 for the video VAE. The
new workflow numbers its nodes differently, so the overrides would land on
the wrong nodes - or on none - and the card would try to load weights it
cannot, which is the failure the overrides exist to prevent.
"""
import json
from pathlib import Path

out = []

cur = json.loads(Path(r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v_audio.json")
                 .read_text(encoding="utf-8"))
new = json.loads(Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
                 .read_text(encoding="utf-8"))

out.append("=== 现用工作流：loader 节点 ===")
for nid, n in cur.items():
    ct = n.get("class_type", "")
    if ct in ("UNETLoader", "CLIPLoader", "VAELoader", "LoraLoaderModelOnly"):
        out.append(f"  #{nid:<5} {ct:<22} "
                   f"{json.dumps(n.get('inputs', {}), ensure_ascii=False)[:90]}")

out.append("")
out.append("=== 新工作流：loader 节点 ===")
for nid, n in new.items():
    ct = n.get("class_type", "")
    if ct in ("UNETLoader", "CLIPLoader", "VAELoader", "LoraLoaderModelOnly"):
        out.append(f"  #{nid:<5} {ct:<22} "
                   f"{json.dumps(n.get('inputs', {}), ensure_ascii=False)[:90]}")

out.append("")
out.append("=== config 里 3090 的 graph_overrides ===")
cfg = Path(r"E:\dramakit\config\default.yaml").read_text(encoding="utf-8")
i = cfg.find("graph_overrides:")
out.append(cfg[i:i + 600] if i > 0 else "  未找到")

out.append("")
out.append("=== config 指向哪个工作流 ===")
for line in cfg.split("\n"):
    if "workflow" in line and not line.strip().startswith("#"):
        out.append("  " + line.strip()[:120])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\compat.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
