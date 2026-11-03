"""Are the card's fast quantised kernels on now?"""
import pathlib
import re

t = pathlib.Path(r"E:\ComfyUI\user\comfyui_8188.log").read_text(
    encoding="utf-8", errors="replace")
m = re.search(r"Found comfy_kitchen backend cuda: (\{.*?\})", t, re.S)
if m:
    blob = m.group(1)
    print("  cuda 后端 disabled =",
          "False" if "'disabled': False" in blob else "**True（还是没开）**")
    caps = re.findall(r"'([a-z0-9_]+)'", blob)
    for want in ("scaled_mm_nvfp4", "w4a8_int8_linear", "convrot_w4a4_linear",
                 "sol_attn", "quantize_nvfp4", "quantize_and_rotate_rowwise"):
        print("    %-28s %s" % (want, "有" if want in caps else "**没有**"))
else:
    print("  日志里没有 cuda 后端那一行")
print()
print("  还有 cu130 的警告吗:", "You need pytorch with cu130" in t)
m2 = re.search(r"pytorch version: (\S+)", t)
print("  torch:", m2.group(1) if m2 else "?")
