"""What ComfyUI thinks this VAE is, asked in its own environment.

The decode failed on a batch norm the file does not contain, and the
loader has a dozen branches keyed on which tensor names are present - so
which branch it took decides whether the file is wrong or the card is
too old to know it. This loads the VAE the same way a job does and prints
the class, the channel count it settled on, and whether a norm came with
it.

Run with ComfyUI's interpreter, since that is where the loader lives.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\ComfyUI")

out = []
try:
    import comfy.sd
    import comfy.utils
    out.append("comfy.sd 导入成功")
except Exception as e:  # noqa: BLE001
    out.append(f"导入失败: {type(e).__name__}: {e}")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\vaeclass.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

path = r"E:\ComfyUI\models\vae\qwen_image_vae.safetensors"
out.append(f"加载 {path}")
try:
    sd = comfy.utils.load_torch_file(path, safe_load=True)
    out.append(f"  张量数 {len(sd)}")
    out.append(f"  有 bn.running_mean: {'bn.running_mean' in sd}")
    out.append(f"  有 decoder.middle.0.residual.0.gamma: "
               f"{'decoder.middle.0.residual.0.gamma' in sd}")
    out.append(f"  有 decoder.upsamples.0.upsamples.0.residual.2.weight: "
               f"{'decoder.upsamples.0.upsamples.0.residual.2.weight' in sd}")
    out.append(f"  decoder.head.2.weight: "
               f"{tuple(sd['decoder.head.2.weight'].shape) if 'decoder.head.2.weight' in sd else '无'}")

    vae = comfy.sd.VAE(sd=sd)
    out.append("")
    out.append("=== 加载结果 ===")
    out.append(f"  type(vae)           = {type(vae).__name__}")
    out.append(f"  latent_channels     = {getattr(vae, 'latent_channels', '?')}")
    out.append(f"  downscale_ratio     = {getattr(vae, 'downscale_ratio', '?')}")
    out.append(f"  upscale_ratio       = {getattr(vae, 'upscale_ratio', '?')}")
    out.append(f"  latent_dim          = {getattr(vae, 'latent_dim', '?')}")
    fsm = getattr(vae, "first_stage_model", None)
    out.append(f"  first_stage_model   = {type(fsm).__name__ if fsm is not None else None}")
    if fsm is not None:
        out.append(f"    有 bn             = {getattr(fsm, 'bn', 'NO ATTR') is not None}")
        bn = getattr(fsm, "bn", None)
        if bn is not None:
            rm = getattr(bn, "running_mean", None)
            out.append(f"    bn.running_mean 形状 = "
                       f"{tuple(rm.shape) if rm is not None else None}")
        zc = getattr(fsm, "z_channels", None) or getattr(fsm, "latent_channels", None)
        out.append(f"    z/latent channels = {zc}")
        # the patch dims the decode rearranges with
        for attr in ("ps", "patch_size", "patchify"):
            if hasattr(fsm, attr):
                out.append(f"    {attr} = {getattr(fsm, attr)}")

    # --- what the model expects -----------------------------------------
    out.append("")
    out.append("=== 对比：模型的 latent 通道 ===")
    upath = r"E:\ComfyUI\models\diffusion_models\krea2_turbo_nvfp4.safetensors"
    usd = comfy.utils.load_torch_file(upath, safe_load=True)
    fw = usd.get("first.weight")
    out.append(f"  first.weight 形状 = {tuple(fw.shape) if fw is not None else '无'}")
    if fw is not None:
        out.append(f"  → 输入维度 {fw.shape[1]}；若 patch=2x2 则 latent 通道 = "
                   f"{fw.shape[1] // 4}")
    out.append(f"  VAE latent_channels = {getattr(vae, 'latent_channels', '?')}")
    out.append("")
    if fw is not None and getattr(vae, "latent_channels", None) == fw.shape[1] // 4:
        out.append("  **一致** — VAE 与模型的通道数匹配")
    else:
        out.append("  **不匹配** — 这就是解码失败的原因")

except Exception as e:  # noqa: BLE001
    import traceback
    out.append(f"加载/检查失败: {type(e).__name__}: {e}")
    out.append(traceback.format_exc()[-1500:])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\vaeclass.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
