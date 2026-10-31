"""The text encoder has to run on native arithmetic, not emulated.

The workflow loads the nvfp4 text encoder.  Ampere has no FP4 tensor
cores - the driver says so itself, "emulated ops: nvfp4" - so every
segment has been paying for a 32B model running on emulated arithmetic.
The same encoder is on the machine in int8_convrot, which Ampere runs
natively.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")

old = """    - name: gpu3090-a
      base_url: http://192.168.31.7:8188
      enabled: true
      roles: [i2v]
      transfer: scp
      ssh_host: 192.168.31.7
      ssh_user: david
      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models
      # 3090 是 Ampere，没有 FP4 张量核：用 int8/convrot 的那套权重
      graph_overrides:
        "6": {unet_name: minimax_h3_ref2va_pruned_int8_convrot.safetensors}
        "11": {vae_name: minimax_h3_video_vae_int8_convrot.safetensors}"""
new = """    - name: gpu3090-a
      base_url: http://192.168.31.7:8188
      enabled: true
      roles: [i2v]
      transfer: scp
      ssh_host: 192.168.31.7
      ssh_user: david
      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models
      # 3090 是 Ampere，没有 FP4 张量核（驱动里 nvfp4 是 emulated）：
      # 主模型、视频 VAE、文本编码器全部走 int8/convrot
      graph_overrides:
        "6": {unet_name: minimax_h3_ref2va_pruned_int8_convrot.safetensors}
        "11": {vae_name: minimax_h3_video_vae_int8_convrot.safetensors}
        "13": {clip_name: qwen3vl_32b_minimax_h3_int8_convrot.safetensors}"""
assert old in s, "gpu3090-a 锚点没找到"
s = s.replace(old, new, 1)

old2 = """    - name: gpu3090-b
      base_url: http://192.168.31.7:8189
      enabled: false                    # 机器现在只剩一张卡，第二个实例起不来
      roles: [i2v]
      transfer: scp
      ssh_host: 192.168.31.7
      ssh_user: david
      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models
      graph_overrides:
        "6": {unet_name: minimax_h3_ref2va_pruned_int8_convrot.safetensors}
        "11": {vae_name: minimax_h3_video_vae_int8_convrot.safetensors}"""
new2 = """    - name: gpu3090-b
      base_url: http://192.168.31.7:8189
      enabled: false                    # 机器现在只剩一张卡，第二个实例起不来
      roles: [i2v]
      transfer: scp
      ssh_host: 192.168.31.7
      ssh_user: david
      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models
      graph_overrides:
        "6": {unet_name: minimax_h3_ref2va_pruned_int8_convrot.safetensors}
        "11": {vae_name: minimax_h3_video_vae_int8_convrot.safetensors}
        "13": {clip_name: qwen3vl_32b_minimax_h3_int8_convrot.safetensors}"""
assert old2 in s, "gpu3090-b 锚点没找到"
s = s.replace(old2, new2, 1)

p.write_text(s, encoding="utf-8")
print("config/default.yaml: 3090 的文本编码器改成 int8_convrot")
