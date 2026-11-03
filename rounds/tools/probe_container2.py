"""What the second container already has, and how the first one gets its GPU.

The working instance reports a device, which means it was given one
somehow - the inspect I read showed no devices and no runtime, so the
request must be recorded somewhere else, and copying the wrong one gives a
container that starts and finds no CUDA.

The half-made second container is read at the same time: if it already has
the mounts and the device, it only needs the right image and a start; if
it is missing either, it is cheaper to replace than to patch.
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


for name in ("comfyui-h3-a", "comfyui-h3-b"):
    out.append(f"=== {name} ===")
    raw = sh(f"docker inspect {name} 2>&1")
    try:
        c = json.loads(raw)[0]
    except Exception:  # noqa: BLE001
        out.append("  " + raw[:600])
        out.append("")
        continue
    hc = c.get("HostConfig") or {}
    cfg = c.get("Config") or {}
    out.append(f"  Image      : {cfg.get('Image')}")
    out.append(f"  Cmd        : {cfg.get('Cmd')}")
    out.append(f"  Env(关键)  : "
               f"{[e for e in (cfg.get('Env') or []) if 'CUDA' in e or 'NVIDIA_VISIBLE' in e]}")
    out.append(f"  PortBindings: {hc.get('PortBindings')}")
    out.append(f"  Binds      : {hc.get('Binds')}")
    out.append(f"  DeviceRequests: {hc.get('DeviceRequests')}")
    out.append(f"  Devices    : {hc.get('Devices')}")
    out.append(f"  Runtime    : {hc.get('Runtime')}")
    out.append(f"  NetworkMode: {hc.get('NetworkMode')}")
    out.append(f"  Restart    : {(hc.get('RestartPolicy') or {}).get('Name')}")
    out.append(f"  State      : {(c.get('State') or {}).get('Status')}")
    out.append("")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\container2.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
