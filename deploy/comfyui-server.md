# ComfyUI 渲染节点部署指南

DramaKit 的画面/视频由你自己的 **ComfyUI 服务器** 生成。本文把它从零装到能被
DramaKit 远程调用，覆盖单机（Windows）、Linux 节点、以及**双 3090 算力池**三种情况。

> 当前技术栈（2026-10）：
> - 出图：**FLUX 3 Image Klein**（5.6B，2026-10-15 发布，ComfyUI 0.42+ 原生支持）
> - 出视频：**MiniMax H3**（I2V，自带配乐/环境声）
> - 多机：`comfyui.nodes` 节点池，按角色派发 + 队列深度调度 + 模型自动同步

---

## 0. 硬件与系统

| 项目 | 最低 | 推荐 |
|------|------|------|
| GPU | 8GB 显存 | 16GB（RTX 5080）/ 24GB（3090） |
| 显存用途 | FLUX 3 int8 版出图 | 出图 + H3 出视频 |
| 内存 | 16GB | 32GB+ |
| 磁盘 | 60GB | 200GB+ SSD（模型很占地方） |
| 系统 | Ubuntu 22.04 / Windows 11 | Ubuntu 22.04 LTS |
| 驱动 | CUDA 12.4+ | CUDA 12.4+ |

---

## 1. Linux 一键部署（单机）

```bash
bash deploy/setup_comfyui.sh          # 默认 ~/ComfyUI
bash deploy/setup_comfyui.sh /opt/ComfyUI
```

脚本会装好系统依赖、ComfyUI、venv + PyTorch、自定义节点、模型目录，并提示你
手动下载模型。

### 需要的模型（体积大，脚本不代下）

| 放哪 | 文件 | 用途 |
|------|------|------|
| `models/diffusion_models/` | `flux3-image-klein-int8-convrot.safetensors` | FLUX 3 出图 |
| `models/text_encoders/` | `qwen3vl_4b_bf16.safetensors` | FLUX 3 文本编码器 |
| `models/text_encoders/` | `minimax_h3_fl2va_*.safetensors`（+ 配套 qwen3vl 32b） | H3 出视频 |
| `models/text_encoders/` | `qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors` | FLUX 3 提示词扩写器（可选） |
| `models/vae/` | `flux2-vae.safetensors` + H3 的 video/audio VAE | 解码 |
| `models/loras/` | `minimax_h3_fl2v_turbo_4step_*.safetensors` | H3 turbo 加速 |

> ⚠️ **文本编码器必须用 bf16 版**。`qwen3vl_4b_int8_convrot` 在 ComfyUI 0.42.0 上
> 会产出垃圾条件：画面颜色语义对但完全没有空间结构。用 bf16 版。

---

## 2. 双 3090 节点（一台机器两个实例）

H3 单任务要吃 15.2G（扩散）+ 14.6G（文本编码），**一张 3090 塞不下两个任务**，
所以要开两个 ComfyUI 实例，各绑一张卡：

```bash
bash deploy/setup_gpu_node.sh          # 默认 ~/ComfyUI，端口 8188 / 8189
```

它会：

- 装 ComfyUI + 依赖 + `ComfyUI-GGUF`
- 建 `models/` 目录（**两个实例共用**，模型只拷一份）
- 注册 `dramakit-comfyui-0.service` / `dramakit-comfyui-1.service`（systemd 开机自启）

手工等价写法：

```bash
CUDA_VISIBLE_DEVICES=0 python main.py --listen 0.0.0.0 --port 8188
CUDA_VISIBLE_DEVICES=1 python main.py --listen 0.0.0.0 --port 8189
```

### 3090 的注意事项

- 3090 是 **Ampere**，没有原生 FP8。BFL 官方说明 30 系 **INT8 比同体积 FP8 更快**
  （INT8 矩阵运算约 2× FP16），所以 H3 用 `w6a8` / `int8_convrot` 是对的选择。
- 24G 显存的余量很大：**专机专用**（这个节点只出视频、不出图）能让 ComfyUI 的
  模型缓存复用，每镜省掉约 78 秒的模型换入开销。

---

## 3. 接入 DramaKit 的节点池

在 DramaKit 的 `config/default.yaml`：

```yaml
comfyui:
  models_dir: E:\\ComfyUI\\models      # 本机 ComfyUI 的模型目录（也是同步的来源）
  nodes:
    - name: gpu3090-v0
      base_url: http://<3090IP>:8188
      roles: [i2v]                     # 只做视频
      transfer: scp                    # shared=已挂载到本机 | scp=走 ssh
      ssh_host: <3090IP>
      ssh_user: ubuntu
      ssh_key: ~/.ssh/id_ed25519
      remote_models: /home/ubuntu/ComfyUI/models
    - name: gpu3090-v1
      base_url: http://<3090IP>:8189
      roles: [i2v]
      transfer: scp
      ssh_host: <3090IP>
      ssh_user: ubuntu
      ssh_key: ~/.ssh/id_ed25519
      remote_models: /home/ubuntu/ComfyUI/models
```

`roles` 决定派发：`t2i` 出图、`i2v` 出视频；**留空 = 什么都接**（本机就是兜底）。
同角色内按**队列深度**挑最闲的节点，某节点中途挂了会自动重派给下一个。

然后：

```bash
dj nodes check            # 连通性 + 版本 + 显存 + 缺哪些模型
dj nodes sync gpu3090-v0  # 把缺的模型传过去（带进度/速度/ETA）
dj nodes sync gpu3090-v1
```

模型清单不用人工维护：**工作流即清单** —— 扫描 `config/comfyui/*.json` 的模型加载
节点自动推出"每个节点需要哪些文件"。

> 节点池里所有节点共用同一套模型文件（清单来自同一份工作流）。
> 想让 3090 用更高质量的 H3 量化版，需要给节点单独配一份工作流（见 TODO）。

---

## 4. 设为后台服务（systemd）

```ini
# /etc/systemd/system/dramakit-comfyui.service
[Unit]
Description=DramaKit ComfyUI
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/ComfyUI
Environment=CUDA_VISIBLE_DEVICES=0
ExecStart=/home/YOUR_USER/ComfyUI/venv/bin/python main.py --listen 0.0.0.0 --port 8188
Restart=always
RestartSec=5
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dramakit-comfyui
journalctl -u dramakit-comfyui -f
```

`TimeoutStartSec=600` 是必要的：H3 每次要换入 15G 权重，systemd 默认 90 秒
会误判成启动失败。

---

## 5. 在 DramaKit 里验证

```bash
dj comfy-test          # 连通 / GPU / 工作流校验 / 模型齐全度
dj nodes               # 节点池总览（角色、队列深度、缺哪些模型）
```

工作流校验会逐节点核对：节点类型在服务器上存在吗、语义 ID（正向提示词、采样器、
UNET/CLIP/VAE 加载器…）指得对吗、模型文件服务器看得见吗。

---

## 6. Windows 单机（本仓库的默认环境）

```bat
:: 启动ComfyUI.bat
cd /d E:\ComfyUI
E:\ComfyUI\venv\Scripts\python.exe main.py --port 8188
```

模型放 `E:\ComfyUI\models`，DramaKit 侧配置：

```yaml
comfyui:
  base_url: http://127.0.0.1:8188
  models_dir: E:\\ComfyUI\\models
```

---

## 7. 常见问题

| 现象 | 原因 / 处理 |
|------|-------------|
| 出图有颜色但没结构 | 文本编码器用了 `int8_convrot`，换成 bf16 版 |
| `dj nodes sync` 传到一半断了 | 用 `transfer: scp`（内置断点续传）或 `shared` 挂载 |
| ComfyUI 报显存不足 | H3 出视频时同机不要跑出图；或让出图节点和视频节点分开（`roles`） |
| systemd 说服务启动失败 | 调大 `TimeoutStartSec`；H3 换入权重很慢 |
| 模型传过去但服务器看不见 | ComfyUI 有缓存，重启实例或等它刷新目录 |
| `dj comfy-test` 说节点类型不存在 | 装对应的自定义节点（`ComfyUI-GGUF` 等） |
