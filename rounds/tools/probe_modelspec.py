"""What ComfyUI decides this model is, and what schedule it will sample with.

The image is noise, which is an under-denoised latent: the schedule did
not match what the model was trained for. The checkpoint declares no
architecture of its own, so the answer comes from whatever the loader
infers - and that is readable directly, without rendering anything.

If it comes back as something other than a flow model with the shift this
family uses, that is the whole explanation.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\ComfyUI")

out = []
try:
    import torch
    import comfy.sd
    import comfy.utils
    import comfy.model_detection
    import comfy.latent_formats
except Exception as e:  # noqa: BLE001
    out.append(f"导入失败: {e}")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\modelspec.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

path = r"E:\ComfyUI\models\diffusion_models\krea2_turbo_nvfp4.safetensors"
out.append(f"=== 加载 {Path(path).name} ===")
sd = comfy.utils.load_torch_file(path, safe_load=True)
out.append(f"  张量数 {len(sd)}")

try:
    model_type = comfy.model_detection.model_detection_from_state_dict(sd)
    out.append(f"  model_detection = {model_type}")
except Exception as e:  # noqa: BLE001
    out.append(f"  model_detection 失败: {type(e).__name__}: {e}")
    model_type = None

# the full diffusion model, the way a job builds it
try:
    model = comfy.sd.DiffusionModel(sd=sd, device=torch.device("cpu"))
    out.append(f"  DiffusionModel = {type(model).__name__}")
    inner = getattr(model, "model", model)
    lf = getattr(inner, "latent_format", None)
    out.append(f"  latent_format = {type(lf).__name__ if lf is not None else None}")
    if lf is not None:
        for attr in ("latent_channels", "scale_factor", "shift_factor",
                     "scaling_factor", "latent_channels"):
            if hasattr(lf, attr):
                out.append(f"      {attr} = {getattr(lf, attr)}")
    # sampling options the model carries
    opts = getattr(model, "model_options", {}) or {}
    out.append(f"  model_options keys = {sorted(opts)}")
    for k in ("sampling", "noise_scaling", "latent_format", "transformer_options"):
        if k in opts:
            out.append(f"    {k} = {str(opts[k])[:300]}")
except Exception as e:  # noqa: BLE001
    import traceback
    out.append(f"  DiffusionModel 失败: {type(e).__name__}: {e}")
    out.append(traceback.format_exc()[-800:])

# --- compare with the flux3 model that renders correctly ---------------
out.append("")
fp = r"E:\ComfyUI\models\diffusion_models\flux3-image-klein-int8-convrot.safetensors"
out.append(f"=== 对照 {Path(fp).name} ===")
try:
    sd2 = comfy.utils.load_torch_file(fp, safe_load=True)
    m2 = comfy.sd.DiffusionModel(sd=sd2, device=torch.device("cpu"))
    inner2 = getattr(m2, "model", m2)
    lf2 = getattr(inner2, "latent_format", None)
    out.append(f"  latent_format = {type(lf2).__name__ if lf2 is not None else None}")
    if lf2 is not None:
        for attr in ("latent_channels", "scale_factor", "shift_factor"):
            if hasattr(lf2, attr):
                out.append(f"      {attr} = {getattr(lf2, attr)}")
    opts2 = getattr(m2, "model_options", {}) or {}
    out.append(f"  model_options keys = {sorted(opts2)}")
except Exception as e:  # noqa: BLE001
    out.append(f"  失败: {e}")

# --- available latent formats ------------------------------------------
out.append("")
out.append("=== comfy.latent_formats 里可用的 ===")
for name in dir(comfy.latent_formats):
    if name.startswith("_"):
        continue
    obj = getattr(comfy.latent_formats, name)
    if isinstance(obj, type):
        try:
            inst = obj()
            ch = getattr(inst, "latent_channels", None)
            sc = getattr(inst, "scale_factor", None)
            sh = getattr(inst, "shift_factor", None)
            out.append(f"  {name:28} channels={ch} scale={sc} shift={sh}")
        except Exception:  # noqa: BLE001
            out.append(f"  {name:28} (无法实例化)")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\modelspec.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
