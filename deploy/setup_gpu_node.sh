#!/usr/bin/env bash
# ============================================================================
#  DramaKit — 双 GPU 渲染节点一键部署 (Ubuntu 22.04 / 两张 3090)
#
#  一台机器开两个 ComfyUI 实例，各绑一张卡：
#      实例 0  CUDA_VISIBLE_DEVICES=0  端口 8188
#      实例 1  CUDA_VISIBLE_DEVICES=1  端口 8189
#
#  两个实例共用同一个 models 目录 —— 所以 H3 那套 ~35G 模型只需传一次，
#  不用拷两遍（DramaKit 的 `dj nodes sync` 就是按这个前提设计的）。
#
#  用法: bash deploy/setup_gpu_node.sh [安装目录，默认 ~/ComfyUI]
#  详见 deploy/comfyui-server.md
# ============================================================================
set -euo pipefail

INSTALL_DIR="${1:-$HOME/ComfyUI}"
PY="${PYTHON:-python3}"
PORT0="${PORT0:-8188}"
PORT1="${PORT1:-8189}"

echo "==> 安装目录: $INSTALL_DIR   端口: $PORT0 / $PORT1"

# ---------------------------------------------------------------- 1) 依赖
echo "==> [1/6] 系统依赖"
sudo apt update -y
sudo apt install -y git wget libgl1 python3-venv python3-pip rsync

# ---------------------------------------------------------------- 2) ComfyUI
echo "==> [2/6] 拉取 ComfyUI"
if [ ! -d "$INSTALL_DIR/.git" ]; then
  git clone https://github.com/comfyanonymous/ComfyUI.git "$INSTALL_DIR"
else
  echo "    已存在，跳过 clone"
fi
cd "$INSTALL_DIR"

# ---------------------------------------------------------------- 3) 环境
echo "==> [3/6] 虚拟环境 + PyTorch + 依赖"
if [ ! -d venv ]; then "$PY" -m venv venv; fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
# 3090 是 Ampere（没有原生 FP8），cu124 通用
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt

echo "==> [3/6] 自定义节点"
cd custom_nodes
clone_if_absent() {
  if [ ! -d "$2" ]; then git clone "$1" "$2"; else echo "    $2 已存在"; fi
}
clone_if_absent https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git ComfyUI-AnimateDiff-Evolved
clone_if_absent https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git ComfyUI-VideoHelperSuite
clone_if_absent https://github.com/ltdrdata/ComfyUI-Manager.git ComfyUI-Manager
clone_if_absent https://github.com/city96/ComfyUI-GGUF.git ComfyUI-GGUF
for n in ComfyUI-AnimateDiff-Evolved ComfyUI-VideoHelperSuite ComfyUI-GGUF; do
  if [ -f "$n/requirements.txt" ]; then pip install -r "$n/requirements.txt" || true; fi
done
cd "$INSTALL_DIR"

# ---------------------------------------------------------------- 4) 模型目录
echo "==> [4/6] 模型目录（两个实例共用）"
mkdir -p models/checkpoints models/diffusion_models models/text_encoders \
         models/vae models/loras models/clip_vision

cat <<'EOF'
    模型不用手工拷 —— 在 DramaKit 那边跑：
        dj nodes sync gpu3090-v0
        dj nodes sync gpu3090-v1
    它按工作流自动推导清单（工作流即清单），缺什么传什么，带进度。
    传输方式二选一（config/default.yaml 的 comfyui.nodes[].transfer）：
        shared  把 models 目录挂载到 DramaKit 所在机器（推荐，零拷贝）
        scp     走 ssh 传（内置断点续传）
EOF

# ---------------------------------------------------------------- 5) systemd
echo "==> [5/6] 注册 systemd 服务（两个实例）"
for i in 0 1; do
  if [ "$i" = "0" ]; then PORT="$PORT0"; else PORT="$PORT1"; fi
  UNIT="/etc/systemd/system/dramakit-comfyui-$i.service"
  sudo tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=DramaKit ComfyUI instance $i (GPU $i)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=CUDA_VISIBLE_DEVICES=$i
Environment=PYTHONUNBUFFERED=1
ExecStart=$INSTALL_DIR/venv/bin/python main.py --listen 0.0.0.0 --port $PORT
Restart=always
RestartSec=5
# 大模型加载需要时间，别让 systemd 嫌它慢
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable dramakit-comfyui-$i
  echo "    dramakit-comfyui-$i.service 已注册（端口 $PORT，GPU $i）"
done

echo "==> [6/6] 完成"
IP="$(hostname -I | awk '{print $1}')"
cat <<EOF

启动:
    sudo systemctl start dramakit-comfyui-0 dramakit-comfyui-1
    journalctl -u dramakit-comfyui-0 -f      # 看日志

自检（在本机）:
    curl -s http://127.0.0.1:$PORT0/system_stats | head -c 200
    curl -s http://127.0.0.1:$PORT1/system_stats | head -c 200

在 DramaKit 的 config/default.yaml 里加（两台 3090 都只做视频，出图留给 5080）:
    comfyui:
      nodes:
        - name: gpu3090-v0
          base_url: http://$IP:$PORT0
          roles: [i2v]
          transfer: scp
          ssh_host: $IP
          ssh_user: $USER
          ssh_key: ~/.ssh/id_ed25519
          remote_models: $INSTALL_DIR/models
        - name: gpu3090-v1
          base_url: http://$IP:$PORT1
          roles: [i2v]
          transfer: scp
          ssh_host: $IP
          ssh_user: $USER
          ssh_key: ~/.ssh/id_ed25519
          remote_models: $INSTALL_DIR/models

然后:
    dj nodes check            # 连通性 + 缺哪些模型
    dj nodes sync gpu3090-v0  # 把模型传过去（带进度）

注意: 节点池里所有节点共用同一套模型文件（清单来自工作流），
      所以两台 3090 跑的是同一个 H3 权重。想让 3090 用更高质量的量化版，
      需要给节点单独配一份工作流（TODO 里记着）。
EOF
