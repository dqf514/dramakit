"""Bring the two remote workers back, and keep them from going down again.

The card stopped answering entirely while the kernel still accepted
connections - the shape a host runs out of memory. Each worker loads
about 45 GB of H3 weights (19.5 GB model + 25.3 GB text encoder), and
until the second worker was enabled only one card ever loaded anything,
so this pressure is new.

Nobody can press the power button at two in the morning, so this tries
for hours: when the door opens it reads what the machine says happened,
restarts the workers, and checks that they answer. The smaller weights
are put in place after that, so the next time it happens there is room
for both.
"""
import json
import subprocess
import time
from pathlib import Path

LOG = Path(r"C:\Users\David\AppData\Local\Temp\opencode\recover8188.txt")
SSH = ["ssh", "-i", r"C:\Users\David\.ssh\id_ed25519",
       "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
       "-o", "BatchMode=yes", "david@192.168.31.8"]
SCRIPT = Path(r"E:\dramakit\rounds\tools\fix_remote_mem.sh")


def note(lines):
    with LOG.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def sh(cmd, timeout=120):
    try:
        r = subprocess.run(SSH + [cmd], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (r.returncode, (r.stdout or "") + (r.stderr or ""))
    except subprocess.TimeoutExpired:
        return 124, "超时"
    except Exception as e:  # noqa: BLE001
        return 1, f"{type(e).__name__}: {e}"


note([f"=== 开始盯着远端（{time.strftime('%H:%M:%S')}）==="])

tries = 0
deadline = time.time() + 8 * 3600
while time.time() < deadline:
    tries += 1
    code, out = sh("echo OK", timeout=60)
    if code != 0:
        if tries % 5 == 1:
            note([f"[{time.strftime('%H:%M:%S')}] 第 {tries} 次：还进不去"])
        time.sleep(40)
        continue

    note([f"[{time.strftime('%H:%M:%S')}] 进去了（第 {tries} 次）"])
    note(["  内存:", "  " + sh("free -g | head -3")[1].strip()])
    note(["  GPU:", "  " + sh(
        "nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total"
        " --format=csv,noheader")[1].strip()])
    note(["  容器:", "  " + sh(
        "docker ps -a --filter name=comfyui-h3"
        " --format '{{.Names}} | {{.Status}}'")[1].strip()])
    note(["  OOM 证据:", "  " + sh(
        "dmesg -T 2>/dev/null | grep -iE 'oom-kill|killed process' | tail -6"
        " || echo '(拿不到)'")[1].strip()])

    # the repair script does the restart and the weight swap
    try:
        subprocess.run(["scp", "-i", r"C:\Users\David\.ssh\id_ed25519",
                        "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
                        str(SCRIPT), "david@192.168.31.8:/tmp/fix_remote_mem.sh"],
                       capture_output=True, text=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        note([f"  上传修复脚本失败: {e}"])

    code, out = sh("bash /tmp/fix_remote_mem.sh 2>&1", timeout=300)
    note([f"[{time.strftime('%H:%M:%S')}] 修复脚本输出:",
          out.strip()[-4000:]])

    for _ in range(12):
        ok = 0
        for p in (8188, 8189):
            c, o = sh(f"curl -s -o /dev/null -w '%{{http_code}}' "
                      f"--max-time 20 http://127.0.0.1:{p}/queue")
            ok += 1 if o.strip() == "200" else 0
            note([f"  :{p} /queue -> {o.strip()}"])
        if ok == 2:
            note([f"[{time.strftime('%H:%M:%S')}] **两个实例都恢复了**"])
            break
        time.sleep(20)
    break

note([f"=== 结束（{time.strftime('%H:%M:%S')}，共试 {tries} 次）==="])
