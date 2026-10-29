"""Give each worker exactly one card.

Both containers were given every card, and the CUDA_VISIBLE_DEVICES in
the environment did not take: the two ComfyUIs loaded their models onto
the same GPU, and the second one ran out of memory. The device list in
the reservation is what decides.
"""
import sys
import time

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"

COMPOSE = """# Two ComfyUI workers, one per RTX 3090.
# Each one gets exactly one card: with "count: all" both of them loaded
# onto the same GPU and the second ran out of memory.
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

  comfyui-h3-b:
    image: comfyui-h3:latest
    container_name: comfyui-h3-b
    restart: unless-stopped
    shm_size: 8gb
    ports:
    - "0.0.0.0:8189:8188"
    environment:
    - CUDA_VISIBLE_DEVICES=0
    deploy:
      resources:
        reservations:
          devices:
          - driver: nvidia
            device_ids: ["1"]
            capabilities: [gpu]
    volumes:
    - /data/comfyui/models:/opt/ComfyUI/models
    - /data/comfyui/input:/opt/ComfyUI/input
    - /data/comfyui/output:/opt/ComfyUI/output
    - /data/comfyui/user:/opt/ComfyUI/user
    - /data/comfyui/custom_nodes:/opt/ComfyUI/custom_nodes
    command: python3 main.py --listen 0.0.0.0 --port 8188 --reserve-vram 1.5
"""

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)


def run(c, timeout=300):
    _in, out, err = cli.exec_command(c, timeout=timeout)
    return (out.read().decode("utf-8", "replace").strip(),
            err.read().decode("utf-8", "replace").strip())


sftp = cli.open_sftp()
with sftp.open(f"/home/{user}/dramakit/docker-compose.h3.yml", "w") as f:
    f.write(COMPOSE)
sftp.close()
print("编组文件已更新（每个实例一张卡）")

o, e = run("docker compose -p dramakit-h3 -f /home/david/dramakit/"
           "docker-compose.h3.yml up -d --force-recreate 2>&1 | tail -6")
print(o or e)

for port in (8188, 8189):
    for i in range(30):
        time.sleep(10)
        o, _e = run(f"curl -s --max-time 6 http://127.0.0.1:{port}/system_stats | "
                    "head -c 80")
        if o:
            print(f"  {port} 起来了")
            break
    else:
        print(f"  {port} 没起来")

o, _e = run("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader")
print(o)
o, _e = run("docker ps --format '{{.Names}} {{.Status}}' | head -6")
print(o)
cli.close()
