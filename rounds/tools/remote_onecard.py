"""One card, one worker.

The machine came back with a single card (nvidia-smi -L lists one RTX
3090), so the second ComfyUI - the one bound to device 1 - cannot start.
The pipeline has to notice that and work with what is there: one worker,
one video at a time.
"""
from pathlib import Path

# 1) the remote compose: one service, the card that is actually there
COMPOSE = """# One ComfyUI worker on the card the machine actually has.
# The second worker (device 1) is left out on purpose: the box came back
# with one card, and asking for a device that is not there stops the
# container from starting at all.
services:
  comfyui-h3-a:
    image: comfyui-h3:latest
    container_name: comfyui-h3-a
    restart: unless-stopped
    shm_size: 8gb
    ports:
    - "0.0.0.0:8188:8188"
    environment:
    - CUDA_VISIBLE_DEVICES=0
    deploy:
      resources:
        reservations:
          devices:
          - driver: nvidia
            device_ids: ["0"]
            capabilities: [gpu]
    volumes:
    - /data/comfyui/models:/opt/ComfyUI/models
    - /data/comfyui/input:/opt/ComfyUI/input
    - /data/comfyui/output:/opt/ComfyUI/output
    - /data/comfyui/user:/opt/ComfyUI/user
    - /data/comfyui/custom_nodes:/opt/ComfyUI/custom_nodes
    command: python3 main.py --listen 0.0.0.0 --port 8188 --reserve-vram 1.5
"""

import paramiko

host = "192.168.31.7"
user = "david"
pw = "dangyang"
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)
sftp = cli.open_sftp()
with sftp.open(f"/home/{user}/dramakit/docker-compose.h3.yml", "w") as f:
    f.write(COMPOSE)
sftp.close()
_in, out, err = cli.exec_command(
    "cd ~ && docker compose -p dramakit-h3 -f ~/dramakit/docker-compose.h3.yml "
    "up -d 2>&1 | tail -5", timeout=300)
print(out.read().decode("utf-8", "replace").strip())
_in, out, err = cli.exec_command(
    "docker ps --format '{{.Names}} | {{.Status}}' | head -6; "
    "nvidia-smi --query-gpu=index,memory.used --format=csv,noheader", timeout=120)
print(out.read().decode("utf-8", "replace").strip())
cli.close()
