"""Document which weight file belongs on which card."""
from pathlib import Path

p = Path(r"E:\\dramakit\\rounds\\README.md")
s = p.read_text(encoding="utf-8")

old = """## 工具"""
new = """## H3 模型矩阵

MiniMax 的 H3 有两个开源 transformer，用途完全不同：

| transformer | 干什么 | 能不能说话 |
|---|---|---|
| `fl2va`（首/末帧 → 视频+音频） | 用首帧（或首尾帧）生成视频 | **不能**——人声出来是乱码 |
| `ref2va`（参考图/视频/音频 → 视频+音频） | 参考图锁身份、参考音频锁音色 | **能**——中文说得清楚 |

所以走"画面+嘴型+人声+音效一次出"这条路，只能用 `ref2va`。实测（whisper 转写）：

```
ref2va + <d>[zh-CN]我想清楚了。</d>   ->  「我想清楚了」   ✓
fl2va  + <d>[zh-CN]我想清楚了。</d>   ->  乱码
```

### 权重文件

放在 `E:\\ComfyUI\\models\\diffusion_models\\`（一个都没删，都留着）：

| 文件 | 大小 | 用在哪 |
|---|---|---|
| `MiniMax_H3_Ref2VA_pruned_nvfp4.safetensors` | 11.7 GB | **5080**（Blackwell 原生 FP4，最快） |
| `MiniMax_H3_FL2VA_pruned_nvfp4.safetensors` | 11.7 GB | 5080，首尾帧版（不说话） |
| `MiniMax_H3_Ref2VA_pruned_mixed_int4_int8_convrot.safetensors` | 14.1 GB | **3090**（Ampere，INT4+INT8+ConvRot） |
| `MiniMax_H3_Ref2VA_pruned_int8_convrot.safetensors` | 19.5 GB | 3090 备用（纯 INT8 ConvRot） |
| `minimax_h3_ref2va_pruned_w6a8.safetensors` | 14.9 GB | 通用（W6A8） |
| `minimax_h3_fl2va_pruned_w6a8.safetensors` | 14.9 GB | 之前用的那一版 |
| `loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors` | 1.8 GB | ref2v 的 4 步加速 LoRA |

3090 还需要的（同样放在 `models\\` 下）：

| 文件 | 大小 |
|---|---|
| `text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors` | 27.1 GB |
| `vae/minimax_h3_video_vae_int8_convrot.safetensors` | 2.8 GB |
| `vae/minimax_h3_audio_vae_fp32.safetensors` | 0.6 GB |

下载走 hf-mirror（这台机器连不上 huggingface.co）。

## 工具"""
assert old in s, "锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("README 已更新")
