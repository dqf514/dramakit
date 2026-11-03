"""What is running on 8188, so the second card can be made the same.

The user wants the other GPU set up the way this one already works - the
same models, the same attention patch, whatever form it happens to be
running in. Reading it is the only way to copy it faithfully: the config
says which weights to override, but the process, the plugins and what is
actually loaded on the card are what decide whether a second instance
renders at all.
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

HOST = "http://192.168.31.8:8188"
SSH = ["ssh", "-i", r"C:\Users\David\.ssh\id_ed25519",
       "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
       "-o", "BatchMode=yes", "david@192.168.31.8"]
out = []


def get(path, timeout=40):
    try:
        with urllib.request.urlopen(HOST + path, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def sh(cmd, timeout=60):
    try:
        r = subprocess.run(SSH + [cmd], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


# --- the card ----------------------------------------------------------
out.append("=== 8188 /system_stats ===")
st = get("/system_stats")
sysinfo = st.get("system", {})
out.append(f"  ComfyUI {sysinfo.get('comfyui_version')}  torch "
           f"{sysinfo.get('torch_version')}")
for d in (st.get("devices") or []):
    out.append(f"  {d.get('name')}  VRAM {d.get('vram_total',0)/2**30:.1f} GB")

out.append("")
out.append("=== 关键自定义节点在不在 ===")
info = get("/object_info")
if "error" in info:
    out.append(f"  读不到: {info['error']}")
else:
    out.append(f"  节点总数 {len(info)}")
    for n in ("PathchSageAttentionKJ", "MiniMaxH3ReferenceToVideo",
              "ComfyMathExpression", "ComfySwitchNode", "PrimitiveBoolean",
              "MarkdownNote", "KSamplerSelect", "BasicScheduler"):
        out.append(f"    {n:32} {'✓' if n in info else '✗ 没有'}")
    # attention modes offered
    spec = info.get("PathchSageAttentionKJ")
    if spec:
        ins = (spec.get("input") or {}).get("required", {})
        modes = ins.get("sage_attention")
        if isinstance(modes, list) and modes and isinstance(modes[0], list):
            out.append(f"    sage_attention 可选: {modes[0]}")

out.append("")
out.append("=== 模型清单 ===")
for folder in ("diffusion_models", "text_encoders", "vae", "loras"):
    o = sh(f"ls -la ~/ComfyUI/models/{folder} 2>/dev/null || "
           f"ls -la /data/comfyui/models/{folder} 2>/dev/null || echo MISSING")
    out.append(f"  {folder}:")
    for line in (o or "").strip().split("\n"):
        if line.strip():
            out.append(f"    {line.strip()[:150]}")

# --- how it is running --------------------------------------------------
out.append("")
out.append("=== 进程 / 容器 ===")
out.append("--- ps ---")
out.append(sh("ps aux | grep -E 'comfyui|main.py|ComfyUI' | grep -v grep | head -12"))
out.append("--- docker ps ---")
out.append(sh("docker ps --format '{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}' 2>&1 | head -12"))
out.append("--- systemd ---")
out.append(sh("systemctl list-units --type=service 2>/dev/null | grep -i comfy | head -8"))

out.append("")
out.append("=== 双卡状态 ===")
out.append(sh("nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv,noheader 2>&1"))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\card8188.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
