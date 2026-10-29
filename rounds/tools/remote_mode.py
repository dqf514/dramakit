"""Switch the other machine between its two modes.

The machine shares the GPUs between the LLM service and ComfyUI, one at a
time: the panel's run mode is just the two containers being up or down.
This stops the LLM and starts ComfyUI (the H3 mode), or the other way
round.
"""
import sys
import time

import paramiko

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.31.7"
user = sys.argv[2] if len(sys.argv) > 2 else "david"
pw = sys.argv[3] if len(sys.argv) > 3 else "dangyang"
mode = sys.argv[4] if len(sys.argv) > 4 else "h3"

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, username=user, password=pw, timeout=20, banner_timeout=30)


def run(c, timeout=180):
    _in, out, err = cli.exec_command(c, timeout=timeout)
    return (out.read().decode("utf-8", "replace").strip(),
            err.read().decode("utf-8", "replace").strip())


if mode == "h3":
    print("切到 H3 模式：停 LLM，起 ComfyUI")
    o, e = run("cd /opt/deploy && docker compose stop vllm-qwen38 2>&1 | tail -3")
    print(o or e)
    o, e = run("cd /opt/deploy && docker compose --profile h3 up -d comfyui 2>&1 | tail -5")
    print(o or e)
else:
    print("切回 LLM 模式：停 ComfyUI，起 LLM")
    o, e = run("cd /opt/deploy && docker compose --profile h3 stop comfyui 2>&1 | tail -3")
    print(o or e)
    o, e = run("cd /opt/deploy && docker compose up -d vllm-qwen38 2>&1 | tail -3")
    print(o or e)

print("等 ComfyUI 起来 ...")
for i in range(40):
    time.sleep(10)
    o, _e = run("docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -E "
                "'comfyui|vllm-qwen38'")
    print(f"  [{i*10:>4}s] {o}")
    if "comfyui" in o and "Up" in o:
        break

o, _e = run("curl -s --max-time 10 http://127.0.0.1:8188/system_stats | head -c 400")
print("system_stats:", o[:400])
o, _e = run("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader")
print(o)
cli.close()
