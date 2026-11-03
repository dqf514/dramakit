"""Which VAE the model wants, told apart by the batch norm's width.

The sampler finished and the decode refused: the latent has sixteen
channels and the VAE's batch norm holds a hundred and twenty-eight. Either
the wrong VAE was downloaded or the wrong model was - the two are told
apart by reading the norm in the file against the patch width in the
model, and by listing what else the card has to decode with.
"""
import json
import struct
import sys
import urllib.request
from pathlib import Path

out = []


def tensors(path: Path) -> dict:
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        meta = json.loads(f.read(n).decode("utf-8"))
    return {k: v for k, v in meta.items() if k != "__metadata__"}


# --- the VAE we have ---------------------------------------------------
vae = Path(r"E:\ComfyUI\models\vae\qwen_image_vae.safetensors")
out.append(f"=== {vae.name} ===")
t = tensors(vae)
bn = {k: v for k, v in t.items() if ".bn." in k or k.startswith("bn.")}
out.append(f"  batch norm 张量: {len(bn)}")
for k in sorted(bn):
    out.append(f"    {k:44} {bn[k].get('shape')}")
out.append(f"  post_quant / conv:")
for k in sorted(t):
    if "post_quant" in k or "quant_conv" in k:
        out.append(f"    {k:44} {t[k].get('shape')}")
out.append(f"  顶层（无前缀）张量:")
for k in sorted(t):
    if "." not in k:
        out.append(f"    {k:44} {t[k].get('shape')}")

# --- the model we have --------------------------------------------------
unet = Path(r"E:\ComfyUI\models\diffusion_models\krea2_turbo_nvfp4.safetensors")
out.append("")
out.append(f"=== {unet.name} ===")
m = tensors(unet)
for k in ("first.weight", "first.bias", "final_layer.linear.weight",
          "final_layer.weight", "out.weight"):
    if k in m:
        out.append(f"  {k:44} {m[k].get('shape')}")
# any hint of latent channels
for k in sorted(m):
    if "patch" in k.lower() or "embed" in k.lower() or k.startswith("first"):
        out.append(f"  {k:44} {m[k].get('shape')}")

# --- every VAE the card can see ----------------------------------------
out.append("")
out.append("=== 卡上所有 VAE ===")
try:
    with urllib.request.urlopen("http://127.0.0.1:8188/object_info/VAELoader",
                                timeout=30) as r:
        spec = json.loads(r.read())
    names = spec["VAELoader"]["input"]["required"]["vae_name"][0]
    for n in names:
        p = Path(r"E:\ComfyUI\models\vae") / n
        size = f"{p.stat().st_size/1024**3:.2f} GiB" if p.exists() else "不在磁盘"
        mark = "  <-- 现用" if n == "qwen_image_vae.safetensors" else ""
        out.append(f"    {n:46} {size}{mark}")
except Exception as e:  # noqa: BLE001
    out.append(f"  读取失败: {e}")

# --- what each VAE's batch norm says -----------------------------------
out.append("")
out.append("=== 各 VAE 的 batch norm 通道数 ===")
for n in (names if "names" in dir() else []):
    p = Path(r"E:\ComfyUI\models\vae") / n
    if not p.exists():
        continue
    try:
        tt = tensors(p)
        b = {k: v for k, v in tt.items() if ".bn." in k or k.startswith("bn.")}
        if b:
            shape = next(iter(b.values())).get("shape")
            out.append(f"    {n:46} bn shape={shape}")
        else:
            out.append(f"    {n:46} 无 batch norm")
    except Exception as e:  # noqa: BLE001
        out.append(f"    {n:46} 读取失败 {e}")

# --- the official template's exact combination --------------------------
out.append("")
out.append("=== 官方模板用的组合 ===")
out.append("  diffusion_models/krea2_turbo_fp8_scaled.safetensors")
out.append("  text_encoders/qwen3vl_4b_fp8_scaled.safetensors")
out.append("  vae/qwen_image_vae.safetensors")
out.append("  latent: EmptyLatentImage")
out.append(f"  我们用的: {unet.name} + qwen3vl_4b_int8_convrot + qwen_image_vae")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\vaechk.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
