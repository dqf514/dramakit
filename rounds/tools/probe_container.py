"""The container's exact shape, so the second one can be made from it.

The working instance is a container rather than a bare process, and what
makes it work is spread across four things that all have to be repeated:
the image, the devices it was given, the models mounted into it, and the
two flags on the command - one of which is the attention patch the whole
point of this card is. Copying the command without the mounts gives a
container that starts and finds no weights; copying the mounts without the
device gives one that finds the weights on the wrong card.

So the inspect output is read and only those four are printed.
"""
import json
import subprocess
import sys
from pathlib import Path

SSH = ["ssh", "-i", r"C:\Users\David\.ssh\id_ed25519",
       "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
       "-o", "BatchMode=yes", "david@192.168.31.8"]
out = []


def sh(cmd, timeout=90):
    try:
        r = subprocess.run(SSH + [cmd], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


# --- the container ------------------------------------------------------
raw = sh("docker inspect comfyui-h3-a 2>&1")
out.append("=== docker inspect comfyui-h3-a ===")
try:
    c = json.loads(raw)[0]
except Exception:  # noqa: BLE001
    out.append(raw[:2000])
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\container.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

out.append(f"  Image   : {c.get('Config', {}).get('Image')}")
out.append(f"  Cmd     : {c.get('Config', {}).get('Cmd')}")
out.append(f"  Entrypoint: {c.get('Config', {}).get('Entrypoint')}")
out.append(f"  Env     :")
for e in (c.get("Config", {}).get("Env") or []):
    out.append(f"      {e}")
out.append("  Ports   :")
for p, binds in ((c.get("HostConfig", {}) or {}).get("PortBindings") or {}).items():
    out.append(f"      {p} -> {binds}")
out.append("  Binds (挂载):")
for b in (c.get("HostConfig", {}) or {}).get("Binds") or []:
    out.append(f"      {b}")
out.append(f"  Devices :")
for d in (c.get("HostConfig", {}) or {}).get("Devices") or []:
    out.append(f"      {d}")
out.append(f"  Runtime : {(c.get('HostConfig') or {}).get('Runtime')}")
out.append(f"  NetworkMode: {(c.get('HostConfig') or {}).get('NetworkMode')}")
out.append(f"  Restart : {(c.get('HostConfig') or {}).get('RestartPolicy')}")

# --- the image ----------------------------------------------------------
out.append("")
out.append("=== 可用镜像 ===")
out.append(sh("docker images --format '{{.Repository}}:{{.Tag}}  {{.Size}}' 2>&1 | head -20"))

# --- where the models live ---------------------------------------------
out.append("")
out.append("=== 模型目录真实路径 ===")
out.append(sh("readlink -f ~/ComfyUI/models 2>&1; echo '---'; "
              "ls -d /data/comfyui/models ~/ComfyUI/models /root/ComfyUI/models 2>&1"))

# --- the second card ----------------------------------------------------
out.append("")
out.append("=== GPU 状态 ===")
out.append(sh("nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv,noheader"))

out.append("")
out.append("=== 已有容器 ===")
out.append(sh("docker ps -a --format '{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}' 2>&1"))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\container.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
