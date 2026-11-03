"""How many channels the VAE decodes from, and what the file actually is.

The sampler finished and the decode refused: the latent arriving has
sixteen channels and the decoder wants a hundred and twenty-eight. Either
the wrong VAE was downloaded, or the wrong empty latent is seeding the
sampler - and the two are told apart by reading the weights rather than
by trying another combination on the card.
"""
import json
import struct
import sys
from pathlib import Path

out = []


def header(path: Path, limit: int = 40) -> dict:
    """The safetensors header: tensor names and dtypes, no data."""
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        raw = f.read(n)
    meta = json.loads(raw.decode("utf-8"))
    tensors = {k: v for k, v in meta.items() if k != "__metadata__"}
    return meta.get("__metadata__"), tensors


for label, rel in (("VAE qwen_image_vae", r"E:\ComfyUI\models\vae\qwen_image_vae.safetensors"),
                   ("UNet krea2_turbo_nvfp4",
                    r"E:\ComfyUI\models\diffusion_models\krea2_turbo_nvfp4.safetensors")):
    p = Path(rel)
    out.append(f"=== {label} ===")
    if not p.exists():
        out.append("  文件不存在")
        out.append("")
        continue
    out.append(f"  {p.stat().st_size/1024**3:.2f} GiB")
    try:
        md, tensors = header(p)
        out.append(f"  __metadata__: {json.dumps(md, ensure_ascii=False)[:300] if md else '无'}")
        out.append(f"  张量数 {len(tensors)}")
        # names that hint at channels
        for name in sorted(tensors):
            low = name.lower()
            if any(k in low for k in ("decoder", "quant_conv", "post_quant",
                                      "conv_in", "conv_first", "in_layers",
                                      "first", "proj_in")):
                shape = tensors[name].get("shape")
                out.append(f"    {name:52} {shape}")
        # the very first and last few names, for structure
        names = sorted(tensors)
        out.append("  前 12 个张量:")
        for name in names[:12]:
            out.append(f"    {name:52} {tensors[name].get('shape')}")
        # any name mentioning latent channels
        for name in names:
            if "latent" in name.lower() or "z_" in name.lower():
                out.append(f"    [latent hint] {name:44} {tensors[name].get('shape')}")
    except Exception as e:  # noqa: BLE001
        out.append(f"  读取失败: {type(e).__name__}: {e}")
    out.append("")

# --- what the card says the VAE accepts --------------------------------
import urllib.request   # noqa: E402
try:
    with urllib.request.urlopen("http://127.0.0.1:8188/object_info/VAEDecode",
                                timeout=30) as r:
        spec = json.loads(r.read())
    out.append("=== VAEDecode 输入 ===")
    out.append("  " + json.dumps(spec.get("VAEDecode", {}).get("input"), ensure_ascii=False))
except Exception as e:  # noqa: BLE001
    out.append(f"读 VAEDecode 规格失败: {e}")

# --- the latent node the template uses, and its channel count ----------
out.append("")
out.append("=== EmptyLatentImage 的实现（看通道数写死在哪）===")
try:
    exe = Path(r"E:\ComfyUI\nodes.py").read_text(encoding="utf-8", errors="replace")
    i = exe.find("class EmptyLatentImage")
    out.append(exe[i:i + 700] if i >= 0 else "  未找到")
except Exception as e:  # noqa: BLE001
    out.append(f"  {e}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\channels.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
