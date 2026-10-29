"""Point the 3090 nodes at the weights that suit their cards."""
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")

old = """      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models
    - name: gpu3090-b"""
new = """      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models
      # 3090 是 Ampere，没有 FP4 张量核：用 int8/convrot 的那套权重
      graph_overrides:
        "6": {unet_name: minimax_h3_ref2va_pruned_int8_convrot.safetensors}
        "11": {vae_name: minimax_h3_video_vae_int8_convrot.safetensors}
    - name: gpu3090-b"""
assert old in s, "锚点没找到"
s = s.replace(old, new, 1)

old = """      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models

"""
new = """      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models
      graph_overrides:
        "6": {unet_name: minimax_h3_ref2va_pruned_int8_convrot.safetensors}
        "11": {vae_name: minimax_h3_video_vae_int8_convrot.safetensors}

"""
if old in s:
    s = s.replace(old, new, 1)
else:
    # the second node ends the list
    i = s.index("- name: gpu3090-b")
    j = s.index("remote_models: /data/comfyui/models", i)
    k = j + len("remote_models: /data/comfyui/models")
    s = (s[:k] + """
      graph_overrides:
        "6": {unet_name: minimax_h3_ref2va_pruned_int8_convrot.safetensors}
        "11": {vae_name: minimax_h3_video_vae_int8_convrot.safetensors}""" + s[k:])

p.write_text(s, encoding="utf-8")
print("yaml: 两个 3090 节点都指向 int8/convrot 的权重")
