"""The text encoder for Ampere, and not the one for Blackwell.

The workflow loads qwen3vl_32b_minimax_h3_nvfp4_awq - the nvfp4 quantized
text encoder, which Blackwell runs on native tensor cores and Ampere
emulates.  The driver on the 3090 says so in its own log: "emulated ops:
nvfp4".  The same encoder is available in int8_convrot, which Ampere runs
natively.

The unet and the video VAE were already switched over by the node's
overrides; the clip was not, so it kept loading the emulated one.
"""
from pathlib import Path
import json

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")

for name in ("gpu3090-a", "gpu3090-b"):
    anchor = f"""    - name: {name}"""
    assert anchor in s, f"没找到节点 {name}"
    # find this node's graph_overrides block
    i = s.find(anchor)
    j = s.find("graph_overrides:", i)
    if j < 0:
        continue
    # the block is:      graph_overrides:\n        "6": {...}\n        "11": {...}
    line_start = s.find("\n", j) + 1
    # insert the clip line right after graph_overrides:
    insert = ('        "13": {clip_name: qwen3vl_32b_minimax_h3_int8_convrot.safetensors}'
              '   # Ampere 没有 FP4 核，nvfp4 是模拟执行的，换 int8 原生核\n')
    if '"13"' in s[j:j+600]:
        print(f"  {name}: 已经有了")
        continue
    s = s[:line_start] + insert + s[line_start:]
    print(f"  {name}: 加了 CLIP 覆盖（int8_convrot）")

p.write_text(s, encoding="utf-8")
print("config/default.yaml: 3090 的文本编码器换成 int8_convrot（永久生效）")
