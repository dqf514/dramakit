"""Watch the card that stopped answering, and bring it back when it can.

One of the two workers stopped answering altogether - the connection is
accepted and nothing comes back, not even an interrupt. The other one is
still working, and the fix in the pool sends the work there instead, so
the run is not held up by it. But a worker that is out is half the
capacity, and until its log has been read there is no way to know why.

So this keeps trying to get in, and the moment it can:
  - reads what the card's own log said before it stopped
  - restarts the container that is not answering
  - records whether it came back

Every attempt is written down, because "it came back" and "it did not" are
different answers and the second one needs a different plan.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

LOG = Path(r"C:\Users\David\AppData\Local\Temp\opencode\recover8188.txt")
SSH = ["ssh", "-i", r"C:\Users\David\.ssh\id_ed25519",
       "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=20",
       "-o", "BatchMode=yes", "david@192.168.31.8"]


def note(lines):
    with LOG.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def sh(cmd, timeout=90):
    try:
        r = subprocess.run(SSH + [cmd], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (r.returncode, (r.stdout or "") + (r.stderr or ""))
    except subprocess.TimeoutExpired:
        return 124, "超时"
    except Exception as e:  # noqa: BLE001
        return 1, f"{type(e).__name__}: {e}"


note([f"=== 开始盯着 8188（{time.strftime('%H:%M:%S')}）==="])

tries = 0
while tries < 60:                      # about an hour of trying
    tries += 1
    code, out = sh("echo OK")
    if code != 0:
        note([f"[{time.strftime('%H:%M:%S')}] 第 {tries} 次：还进不去（{out.strip()[:60]}）"])
        time.sleep(45)
        continue

    note([f"[{time.strftime('%H:%M:%S')}] 进去了（第 {tries} 次）"])
    note(["  GPU:", "  " + sh("nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader")[1].strip()])
    note(["  容器:", "  " + sh("docker ps -a --filter name=comfyui-h3 --format '{{.Names}} | {{.Status}}'")[1].strip()])
    for c in ("comfyui-h3-a", "comfyui-h3-b"):
        code, logs = sh(f"docker logs --tail 40 {c} 2>&1")
        note([f"  {c} 日志尾:", "  " + logs.strip()[-2500:]])

    # restart the one that is not answering
    code, out = sh(
        "docker restart comfyui-h3-a 2>&1 | tail -2")
    note([f"[{time.strftime('%H:%M:%S')}] 重启 comfyui-h3-a: {out.strip()[:200]}"])
    time.sleep(45)
    code, out = sh("curl -s -o /dev/null -w '%{http_code}' --max-time 20 http://127.0.0.1:8188/queue")
    note([f"[{time.strftime('%H:%M:%S')}] 重启后 8188 /queue -> {out.strip()}"])

    # does it answer now?
    for _ in range(10):
        code, out = sh("curl -s -o /dev/null -w '%{http_code}' --max-time 20 http://127.0.0.1:8188/queue")
        if out.strip() == "200":
            note([f"[{time.strftime('%H:%M:%S')}] **8188 恢复了**"])
            break
        time.sleep(15)
    else:
        note([f"[{time.strftime('%H:%M:%S')}] 重启后 8188 仍不回答"])
    break

note([f"=== 结束（{time.strftime('%H:%M:%S')}，共试 {tries} 次）==="])
