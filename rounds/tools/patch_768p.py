"""The 8-step LoRA for 768p, and the picture to match.

The LoRA is the one trained for eight steps at 768p - which is the
resolution the H3 model was made for (1344x768 in landscape).  The
resolution goes up to it everywhere, so the picture, the references and
the finished episode are all the same size.
"""
from pathlib import Path
import json
import re

ROOT = Path(r"E:\\dramakit")

# --------------------------------------------------------------------------- #
# 1. the workflow: the new LoRA
# --------------------------------------------------------------------------- #
p = ROOT / "config\\comfyui\\i2v_minimax_h3_ref2v_audio.json"
d = json.loads(p.read_text(encoding="utf-8"))
NEW_LORA = "minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors"
changed = False
for nid, node in d.items():
    if isinstance(node, dict) and node.get("class_type") == "LoraLoaderModelOnly":
        cur = (node.get("inputs") or {}).get("lora_name", "")
        if "ref2v_turbo_8step" not in cur:
            node["inputs"]["lora_name"] = NEW_LORA
            node["inputs"]["strength_model"] = 1.0
            changed = True
            print(f"工作流: 节点{nid} 的 LoRA -> {NEW_LORA}")
if changed:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

# --------------------------------------------------------------------------- #
# 2. the sizes: 768p everywhere
# --------------------------------------------------------------------------- #
c = ROOT / "config\\default.yaml"
s = c.read_text(encoding="utf-8")
pairs = [
    ("  width: 1024                             # 出图分辨率（FLUX 3 / H3 都吃 32 的倍数）\n"
     "  height: 576                             # 16:9 横屏",
     "  width: 1344                             # 出图分辨率（H3 原生 768p，FLUX 同尺寸）\n"
     "  height: 768                             # 16:9 横屏 768p"),
    ("  video_width: 1024                      # 16:9 横屏\n  video_height: 576",
     "  video_width: 1344                      # 16:9 横屏 768p（H3 原生）\n  video_height: 768"),
    ("  width: 1024\n  height: 576                             # 16:9 横屏成片",
     "  width: 1344\n  height: 768                             # 16:9 横屏 768p 成片"),
    ("  ref_width: 1024                               # 面部满屏照：跟出图同尺寸（16:9）\n"
     "  ref_height: 576\n"
     "  ref_body_width: 576                           # 全身视图用竖幅：宽幅里人太小、灰底太多\n"
     "  ref_body_height: 1024",
     "  ref_width: 1344                               # 面部满屏照：跟出图同尺寸（16:9 768p）\n"
     "  ref_height: 768\n"
     "  ref_body_width: 768                           # 全身视图用竖幅：宽幅里人太小、灰底太多\n"
     "  ref_body_height: 1344"),
]
for old, new in pairs:
    if new in s:
        print("  配置: 已经改过了")
        continue
    assert old in s, f"配置锚点没找到:\n{old[:120]}"
    s = s.replace(old, new, 1)
c.write_text(s, encoding="utf-8")
print("config/default.yaml: 全线 1344x768（768p）")
