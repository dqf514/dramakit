"""Run the remaining rounds back to back.

Each round is a separate process, so a fix committed between rounds lands in
the next one.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"E:\dramakit")
PY = str(ROOT / "venv" / "Scripts" / "python.exe")

start = int(sys.argv[1]) if len(sys.argv) > 1 else 4
end = int(sys.argv[2]) if len(sys.argv) > 2 else 10

for n in range(start, end + 1):
    print(f"\n########## 第 {n} 轮 开始 ({time.strftime('%H:%M')}) ##########", flush=True)
    t0 = time.time()
    r = subprocess.run([PY, str(ROOT / "round.py"), "--round", str(n)],
                       cwd=str(ROOT), capture_output=True, text=True,
                       errors="replace")
    print(r.stdout[-1500:], flush=True)
    if r.stderr:
        print("stderr:", r.stderr[-400:], flush=True)
    print(f"########## 第 {n} 轮 结束，用时 {(time.time()-t0)/60:.1f} 分钟 "
          f"(exit={r.returncode}) ##########", flush=True)
print("全部轮次结束", flush=True)
