# ComfyUI 视频服务器部署完整指南

DramaKit 的画面/视频由你自己的 **ComfyUI 服务器** 生成。本文档把它从零装到能被
DramaKit 远程调用，覆盖 Linux（推荐，生产）和 Windows 两种情况。

> 目标：一台装了 ComfyUI + AnimateDiff（图生视频）的机器，监听 `0.0.0.0:8188`，
> DramaKit 通过 `comfyui.base_url` 远程提交工作流、拉取成片。

---

## 0. 硬件与系统建议

| 项目 | 最低 | 推荐 |
|------|------|------|
| GPU | 8GB 显存（RTX 3060/A2000） | 12~24GB（RTX 4070Ti/4090/A5000） |
| 显存用途 | SDXL 出图 | SDXL 出图 + AnimateDiff 视频 |
| 内存 | 16GB | 32GB+ |
| 磁盘 | 50GB | 200GB+ SSD（模型很占地方） |
| 系统 | Ubuntu 22.04 / Windows 11 | Ubuntu 22.04 LTS |
| 驱动 | CUDA 12.1+ | CUDA 12.4+ |

8GB 显存（如你笔记本的 A2000）能跑 SDXL 出图和短视频 AnimateDiff；长视频/高分辨率
建议上 12GB+ 或改用云端 GPU 服务器。

---

## 1. Linux 一键部署（推荐）

```bash
# 1) 基础依赖
sudo apt update && sudo apt install -y git python3-venv python3-pip wget libgl1

# 2) 拉取 ComfyUI
cd ~ && git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 3) 独立虚拟环境
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt

# 4) 关键自定义节点（视频必需）
cd custom_nodes
git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
git clone https://github.com/ltdrdata/ComfyUI-Manager.git     # 方便日后管理节点
cd ComfyUI-AnimateDiff-Evolved && pip install -r requirements.txt && cd ..
cd ComfyUI-VideoHelperSuite && pip install -r requirements.txt && cd ..
cd ../..

# 5) 首次启动（--listen 让它能被远程访问）
source venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188
```

也可以直接用本仓库脚本：`bash deploy/setup_comfyui.sh`（见下）。

---

## 2. 下载模型

放到 ComfyUI 对应目录：

**出图（SDXL，写实短剧推荐）** → `models/checkpoints/`
- `sd_xl_base_1.0.safetensors`（官方基模）
- 或写实向微调：`juggernautXL`、`realvisxl`（Civitai 下载）

**图生视频（AnimateDiff）** → `models/animatediff_models/`
- `mm_sd_v15_v2.ckpt`（AnimateDiff 运动模型，配 SD1.5）
- 运动模型目录若不存在就手动建：`mkdir -p models/animatediff_models`
- AnimateDiff 还需要 SD1.5 底模 → `models/checkpoints/v1-5-pruned-emaonly.safetensors`

**VAE / LoRA（可选）** → `models/vae/`、`models/loras/`
- 角色一致性可训练角色 LoRA 放这里，然后在工作流里挂 LoRA 节点。

下载示例：
```bash
cd ~/ComfyUI
wget -P models/checkpoints/ https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
wget -P models/checkpoints/ https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
mkdir -p models/animatediff_models
wget -P models/animatediff_models/ https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt
```

---

## 3. 设为后台服务（systemd，开机自启）

`sudo nano /etc/systemd/system/comfyui.service`：

```ini
[Unit]
Description=ComfyUI Server
After=network.target

[Service]
Type=simple
User=你的用户名
WorkingDirectory=/home/你的用户名/ComfyUI
ExecStart=/home/你的用户名/ComfyUI/venv/bin/python main.py --listen 0.0.0.0 --port 8188
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用：
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now comfyui
sudo systemctl status comfyui        # 看是否 running
journalctl -u comfyui -f             # 看实时日志
```

---

## 4. 让 DramaKit 所在机器能访问（网络/防火墙）

**同机**：`base_url: http://127.0.0.1:8188` 即可。

**局域网/远程**：
```bash
# 放行 8188（ufw 示例）
sudo ufw allow 8188/tcp
```
- 云服务器还要在**安全组/防火墙**放行 8188 入站。
- DramaKit 配置改成：`comfyui.base_url: http://<服务器IP>:8188`。
- **安全提醒**：ComfyUI 默认无鉴权，公网暴露有风险。生产环境建议：
  - 只在内网/VPN 内暴露；或
  - 用 Nginx 反代 + Basic Auth / IP 白名单；或
  - SSH 隧道：`ssh -L 8188:127.0.0.1:8188 user@server`，然后 DramaKit 连 `http://127.0.0.1:8188`。

Nginx 反代 + Basic Auth 示例：
```nginx
server {
    listen 80;
    server_name comfy.example.com;
    auth_basic "ComfyUI";
    auth_basic_user_file /etc/nginx/.htpasswd;
    location / {
        proxy_pass http://127.0.0.1:8188;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;      # WebSocket 进度必需
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 600s;
    }
}
```
> 注意：DramaKit 用 WebSocket 监听生成进度，反代必须转发 `Upgrade/Connection` 头。

---

## 5. 导出你自己的工作流并对上节点ID

DramaKit 内置的 `config/comfyui/*.json` 是**模板**，你的图很可能不一样。正确做法：

1. 在 ComfyUI 网页里搭好一个能正常出图/出视频的工作流。
2. 打开右上角设置 → 勾选 **Dev mode Options**。
3. 菜单点 **Save (API Format)**，导出成 JSON。
4. 覆盖 `config/comfyui/t2i_sdxl.json`（或改配置里的路径）。
5. 打开导出的 JSON，找到这些节点的 **ID**（就是 JSON 里的键），填到 `config/default.yaml`：

   **出图 `t2i_nodes`**
   | 语义 | 对应节点类型 | 要写的字段 |
   |------|-------------|-----------|
   | positive | CLIPTextEncode（正向） | text |
   | negative | CLIPTextEncode（负向） | text |
   | seed | KSampler | seed / noise_seed |
   | width, height | EmptyLatentImage | width / height |
   | steps, cfg, sampler | KSampler | steps / cfg / sampler_name / scheduler |
   | checkpoint | CheckpointLoaderSimple | ckpt_name |

   **图生视频 `i2v_nodes`**
   | 语义 | 对应节点类型 | 字段 |
   |------|-------------|------|
   | image | LoadImage | image（DramaKit 会先上传再写名字） |
   | positive/negative | CLIPTextEncode | text |
   | seed | KSampler | seed |
   | frames | EmptyLatentImage / ADE Context | batch_size / length / frames / context_length |
   | fps | VHS_VideoCombine | frame_rate / fps |

6. 校验连通：`dj doctor`（会 ping ComfyUI）。

> 任何额外参数（如挂 LoRA、换 VAE、控制网）可以在代码里通过 `extra.graph_overrides`
> 传 `{"节点ID": {"字段": 值}}` 直接注入，不用改工作流文件。

---

## 6. Windows 部署（备选）

```bat
:: 1) 装 Python 3.11+ 和 Git，然后：
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python -m venv venv
venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt

:: 2) 自定义节点
cd custom_nodes
git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
cd ..

:: 3) 启动（监听所有网卡）
python main.py --listen 0.0.0.0 --port 8188
```
防火墙放行 8188：
```bat
netsh advfirewall firewall add rule name="ComfyUI" dir=in action=allow protocol=TCP localport=8188
```

---

## 7. 常见问题

- **DramaKit 报 `ComfyUI 不可达`**：确认 `python main.py --listen 0.0.0.0` 起了、防火墙放行、
  `base_url` 的 IP/端口对。浏览器直接开 `http://IP:8188` 能看到界面才算通。
- **出图全是黑图/报错**：多半是 checkpoint 名字对不上，改 `comfyui.checkpoint` 或工作流里的
  `ckpt_name` 为你 `models/checkpoints/` 里真实的文件名。
- **视频不动/报错**：AnimateDiff 运动模型没下好，或 `i2v_nodes` 的 frames/fps 节点ID对不上。
  先在 ComfyUI 网页里手动跑通再对接。
- **显存不足 OOM**：降低 `comfyui.width/height`（如 512x896）、减小 `frames`，或加 `--lowvram`
  启动参数。
- **进度卡住不动**：反代没转发 WebSocket。见第 4 节 Nginx 的 `Upgrade/Connection` 头。
