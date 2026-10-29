"""Write down how the 3090 is set up."""
from pathlib import Path

p = Path(r"E:\\dramakit\\rounds\\README.md")
s = p.read_text(encoding="utf-8")

old = """### 权重文件"""
new = """### 3090 节点（192.168.31.7）

那台机器是**双 3090**（各 24G），本来在跑 Qwen3.8-27B-FP8 的 API 服务
（vLLM）。显存是**分时复用**的：跑 H3 的时候把 LLM 停掉。

现在的状态：**H3 模式常开**（LLM 暂时不用），两个 ComfyUI 实例各占一张卡：

| 实例 | 端口 | 显卡 | 容器 |
|---|---|---|---|
| gpu3090-a | 8188 | GPU 0 | `comfyui-h3-a` |
| gpu3090-b | 8189 | GPU 1 | `comfyui-h3-b` |

编组文件在远端 `~/dramakit/docker-compose.h3.yml`（自己的目录，不动
`/opt/deploy` 那份生产用的）。开关：

```bash
ssh david@192.168.31.7
# 切到 H3
cd /opt/deploy && docker compose stop vllm
docker compose -p dramakit-h3 -f ~/dramakit/docker-compose.h3.yml up -d
# 切回 LLM
docker compose -p dramakit-h3 -f ~/dramakit/docker-compose.h3.yml down
cd /opt/deploy && docker compose up -d vllm
```

已经配好的：免密密钥（本机 `~/.ssh/id_ed25519` 已放进远端
`~/.ssh/authorized_keys`）、david 在 docker 组里（可以直接 `docker compose`）、
远端 `models/` 里 H3 的权重齐全。

流水线里的分工：

- **本机 5080**：只出图（FLUX 3，nvfp4 权重）——`local_roles: [t2i]`
- **两台 3090**：只出视频（H3 ref2va，int8/convrot 权重）——`roles: [i2v]`

每个节点可以用自己的权重（`graph_overrides`）：

```yaml
- name: gpu3090-a
  base_url: http://192.168.31.7:8188
  roles: [i2v]
  ssh_host: 192.168.31.7
  ssh_user: david
  ssh_key: C:/Users/David/.ssh/id_ed25519
  remote_models: /data/comfyui/models
  graph_overrides:
    "6":  {unet_name: minimax_h3_ref2va_pruned_int8_convrot.safetensors}
    "11": {vae_name: minimax_h3_video_vae_int8_convrot.safetensors}
```

（3090 是 Ampere，没有 FP4 张量核，所以用 int8/convrot 那套；5080 用 nvfp4。）

### 权重文件"""
assert old in s, "锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("README 已更新（3090 节点）")
