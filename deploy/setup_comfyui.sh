#!/usr/bin/env bash
# ===========================================================================
#  DramaKit — ComfyUI 视频服务器一键部署 (Linux / Ubuntu 22.04)
#  用法: bash deploy/setup_comfyui.sh [安装目录，默认 ~/ComfyUI]
#  详见 deploy/comfyui-server.md
# ===========================================================================
set -euo pipefail

INSTALL_DIR="${1:-$HOME/ComfyUI}"
PY="${PYTHON:-python3}"

echo "==> 安装目录: $INSTALL_DIR"

echo "==> [1/6] 系统依赖"
sudo apt update -y
sudo apt install -y git wget libgl1 python3-venv python3-pip

echo "==> [2/6] 拉取 ComfyUI"
if [ ! -d "$INSTALL_DIR" ]; then
  git clone https://github.com/comfyanonymous/ComfyUI.git "$INSTALL_DIR"
else
  echo "    已存在，跳过 clone"
fi
cd "$INSTALL_DIR"

echo "==> [3/6] 虚拟环境 + PyTorch(CUDA 12.4) + 依赖"
if [ ! -d venv ]; then "$PY" -m venv venv; fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt

echo "==> [4/6] 视频相关自定义节点"
cd custom_nodes
clone_if_absent() {
  if [ ! -d "$2" ]; then git clone "$1" "$2"; else echo "    $2 已存在"; fi
}
clone_if_absent https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git ComfyUI-AnimateDiff-Evolved
clone_if_absent https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git ComfyUI-VideoHelperSuite
clone_if_absent https://github.com/ltdrdata/ComfyUI-Manager.git ComfyUI-Manager
for n in ComfyUI-AnimateDiff-Evolved ComfyUI-VideoHelperSuite; do
  if [ -f "$n/requirements.txt" ]; then pip install -r "$n/requirements.txt" || true; fi
done
cd "$INSTALL_DIR"

echo "==> [5/6] 模型目录"
mkdir -p models/checkpoints models/animatediff_models models/vae models/loras
cat <<'EOF'
    请手动下载模型（体积大，脚本不代下）：
      models/checkpoints/sd_xl_base_1.0.safetensors          (SDXL 出图)
      models/checkpoints/v1-5-pruned-emaonly.safetensors     (AnimateDiff 底模)
      models/animatediff_models/mm_sd_v15_v2.ckpt            (运动模型)
    下载命令见 deploy/comfyui-server.md 第 2 节。
EOF

echo "==> [6/6] 完成"
cat <<EOF

启动（可被远程访问）:
  cd $INSTALL_DIR && source venv/bin/activate
  python main.py --listen 0.0.0.0 --port 8188

设为开机自启服务:
  参考 deploy/comfyui-server.md 第 3 节 (systemd)

然后在 DramaKit 的 config/default.yaml 里设置:
  comfyui.base_url: http://<本机IP>:8188
校验连通:
  dj doctor
EOF
