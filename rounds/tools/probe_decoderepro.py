"""Reproduce the decode outside the server, so the two accounts can be told apart.

Loading the VAE on its own says the channels match; running a job says
they do not. Only one of those can be right, and the difference is
whether the failure depends on how the job got here - the sampler's output
rather than an empty latent, or a VAE cached from an earlier run.

So a latent of the size the sampler would produce is decoded directly, and
if that works, a second attempt replays the job's own path.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\ComfyUI")

out = []
try:
    import torch
    import comfy.sd
    import comfy.utils
    import comfy.model_management
except Exception as e:  # noqa: BLE001
    out.append(f"导入失败: {e}")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\decoderepro.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

vae_path = r"E:\ComfyUI\models\vae\qwen_image_vae.safetensors"
sd = comfy.utils.load_torch_file(vae_path, safe_load=True)
vae = comfy.sd.VAE(sd=sd)
out.append(f"VAE latent_channels = {vae.latent_channels}")
fsm = vae.first_stage_model
out.append(f"first_stage_model = {type(fsm).__name__}")
bn = getattr(fsm, "bn", None)
out.append(f"fsm.bn = {bn}")
if bn is not None:
    out.append(f"  type = {type(bn).__name__}")
    for attr in ("running_mean", "running_var", "weight", "bias", "num_features"):
        v = getattr(bn, attr, None)
        if v is not None:
            out.append(f"  {attr} 形状 = {tuple(v.shape) if hasattr(v, 'shape') else v}")

# --- the decode the job performed ---------------------------------------
# 768x1344 image, latent at 1/8 scale, 16 channels, batch 1
w, h, c = 1344, 768, 16
lw, lh = w // 8, h // 8
out.append("")
out.append(f"=== 造一个 {c}x{lh}x{lw} 的 latent 去解码 ===")
z = torch.zeros((1, c, lh, lw))
try:
    with comfy.model_management.vram_state():
        img = vae.decode(z)
    out.append(f"  **成功** 输出形状 {tuple(img.shape)}")
except Exception as e:  # noqa: BLE001
    out.append(f"  **失败** {type(e).__name__}: {e}")

# --- and with the channels the norm wants ------------------------------
out.append("")
out.append("=== 再试 128 通道 ===")
z2 = torch.zeros((1, 128, lh, lw))
try:
    with comfy.model_management.vram_state():
        img = vae.decode(z2)
    out.append(f"  **成功** 输出形状 {tuple(img.shape)}")
except Exception as e:  # noqa: BLE001
    out.append(f"  **失败** {type(e).__name__}: {e}")

# --- what the model would emit -----------------------------------------
out.append("")
out.append("=== 模型的输出投影 ===")
upath = r"E:\ComfyUI\models\diffusion_models\krea2_turbo_nvfp4.safetensors"
usd = comfy.utils.load_torch_file(upath, safe_load=True)
for k in sorted(usd):
    if any(t in k for t in ("final", "out.", "head", "adaLN", "modulation.out")):
        out.append(f"  {k:44} {tuple(usd[k].shape)}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\decoderepro.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
