"""What the checkpoint says about itself, and what the sampler was told.

The image came out as noise, which is what an under-denoised latent looks
like: the sampling schedule did not match what the model was trained for.
A model can carry that answer inside its own metadata, and a workflow can
carry it in a sampling node - the official one has no such node, so if
this file declares nothing either, the two differ in some other way.

The metadata is printed whole rather than searched for one key, because
the name of the thing that is missing is not known in advance.
"""
import json
import struct
import sys
from pathlib import Path

out = []


def meta_of(path: Path) -> dict:
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        m = json.loads(f.read(n).decode("utf-8"))
    return m.get("__metadata__") or {}, {k: v for k, v in m.items()
                                         if k != "__metadata__"}


for label, rel in (("krea2_turbo_nvfp4",
                    r"E:\ComfyUI\models\diffusion_models\krea2_turbo_nvfp4.safetensors"),
                   ("flux3-image-klein（对照，能出图）",
                    r"E:\ComfyUI\models\diffusion_models\flux3-image-klein-int8-convrot.safetensors")):
    p = Path(rel)
    out.append(f"=== {label} ===")
    if not p.exists():
        out.append("  不存在")
        out.append("")
        continue
    md, tensors = meta_of(p)
    out.append(f"  __metadata__ ({len(md)} 项):")
    for k in sorted(md):
        v = str(md[k])
        out.append(f"    {k} = {v[:400]}")
    if not md:
        out.append("    （空）")
    # keys that look like config
    out.append("  可能的配置键:")
    for k in sorted(tensors):
        if any(t in k.lower() for t in ("config", "latent_format", "sampling",
                                        "arch", "params")):
            out.append(f"    {k} = {str(tensors[k])[:200]}")
    out.append("")

# --- what the working flux3 workflow does about sampling ---------------
import json as J   # noqa: E402
wf = Path(r"E:\dramakit\config\comfyui\t2i_flux3_klein.json")
out.append("=== 能出图的 flux3 工作流：采样相关节点 ===")
g = J.loads(wf.read_text(encoding="utf-8"))
for nid, n in g.items():
    ct = n.get("class_type", "")
    if any(t in ct for t in ("ModelSampling", "KSampler", "Sampler")):
        out.append(f"  #{nid} {ct}: {J.dumps(n.get('inputs'), ensure_ascii=False)[:220]}")

out.append("")
out.append("=== 我们的 krea2 工作流 ===")
g2 = J.loads(Path(r"E:\dramakit\config\comfyui\t2i_krea2.json").read_text(encoding="utf-8"))
for nid, n in g2.items():
    ct = n.get("class_type", "")
    if any(t in ct for t in ("ModelSampling", "KSampler", "Sampler")):
        out.append(f"  #{nid} {ct}: {J.dumps(n.get('inputs'), ensure_ascii=False)[:220]}")

# --- what sampling nodes the card has ----------------------------------
import urllib.request   # noqa: E402
out.append("")
out.append("=== 卡上的 ModelSampling* 节点 ===")
try:
    with urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=40) as r:
        info = J.loads(r.read())
    for name in sorted(info):
        if "modelsampling" in name.lower() or name in ("ModelSamplingFlux",):
            ins = (info[name].get("input") or {}).get("required", {})
            out.append(f"  {name}: {list(ins)}")
except Exception as e:  # noqa: BLE001
    out.append(f"  {e}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\modelmeta.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
