"""Add the two 3090 workers to the pipeline's node list."""
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")

old = "  nodes: []"
if old in s:
    new = """  # 节点池：除本机之外的 ComfyUI 机器。
  # 3090 是双卡，一台 ComfyUI 只用一张卡，所以那边跑两个实例（8188 / 8189）。
  # 这台机器的显存是分时复用的：跑 H3 之前要把 LLM 服务停下来。
  nodes:
    - name: gpu3090-a
      base_url: http://192.168.31.7:8188
      enabled: true
      roles: [i2v]
      transfer: scp
      ssh_host: 192.168.31.7
      ssh_user: david
      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models
    - name: gpu3090-b
      base_url: http://192.168.31.7:8189
      enabled: true
      roles: [i2v]
      transfer: scp
      ssh_host: 192.168.31.7
      ssh_user: david
      ssh_key: C:/Users/David/.ssh/id_ed25519
      remote_models: /data/comfyui/models"""
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("yaml: 两个 3090 节点已加")
else:
    print("锚点没找到，现有 nodes 行:")
    for line in s.splitlines():
        if "nodes" in line and "NodeConfig" not in line:
            print("   ", line)
