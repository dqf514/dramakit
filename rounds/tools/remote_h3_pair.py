"""Put two ComfyUI instances on the other machine, one per GPU.

The machine has two 3090s. One ComfyUI only ever uses one of them, so the
second card would sit idle. Two instances, one per card, give the pipeline
two workers: the shots are spread over them and the episode takes half
the wall clock.

The LLM service has to give the cards up first - the two modes share the
same memory, by time, not at the same time.
"""
import sys
import time

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"
mode = sys.argv[4] if len(sys.argv) > 4 else "h3"

COMPOSE = """# Two ComfyUI workers, one per RTX 3090.
# The LLM service and these share the cards by time: the run mode decides
# which of them is up.
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
            count: all
            capabilities:
            - gpu
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
    - CUDA_VISIBLE_DEVICES=1
    deploy:
      resources:
        reservations:
          devices:
          - driver: nvidia
            count: all
            capabilities:
            - gpu
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


# 1) the compose file (in the user's own directory: /opt/deploy is root's)
sftp = cli.open_sftp()
home = f"/home/{user}/dramakit"
try:
    sftp.stat(home)
except FileNotFoundError:
    cli.exec_command(f"mkdir -p {home}")
with sftp.open(f"{home}/docker-compose.h3.yml", "w") as f:
    f.write(COMPOSE)
sftp.close()
o, e = run(f"ls -la {home}/docker-compose.h3.yml")
print(o or e)

# 2) the switch
if mode == "h3":
    print("切到 H3 模式")
    o, e = run("cd /opt/deploy && docker compose stop vllm 2>&1 | tail -2")
    print(o or e)
    o, e = run("docker compose -p dramakit-h3 -f /home/david/dramakit/docker-compose.h3.yml "
               "up -d 2>&1 | tail -6")
    print(o or e)
else:
    print("切回 LLM 模式")
    o, e = run("docker compose -p dramakit-h3 -f /home/david/dramakit/docker-compose.h3.yml "
               "down 2>&1 | tail -4")
    print(o or e)
    o, e = run("cd /opt/deploy && docker compose up -d vllm 2>&1 | tail -3")
    print(o or e)

# 3) wait for the servers
for port in (8188, 8189):
    print(f"等 {port} ...")
    for i in range(60):
        time.sleep(10)
        o, _e = run(f"curl -s --max-time 6 http://127.0.0.1:{port}/system_stats | "
                    "head -c 120")
        if o:
            print(f"  {port} 起来了: {o[:110]}")
            break
    else:
        print(f"  {port} 没起来")

o, _e = run("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader")
print(o)
o, _e = run("docker ps --format '{{.Names}} {{.Status}}' | head -8")
print(o)
cli.close()
