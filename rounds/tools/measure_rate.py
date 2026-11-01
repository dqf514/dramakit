"""How fast is the prompt stage going, and how much is left?

Nothing is written until the end, so the count on disk says only that the
stage has not finished. The sheets it makes on first meeting a character
are the one thing that appears as it goes, so watching those - and the
process itself - gives a rate.
"""
import subprocess
import time
from pathlib import Path

root = Path(r"E:\dramakit\projects\魔兽世界")


def sheets():
    return sorted(f for f in root.rglob("sheet.*"))


def procs():
    r = subprocess.run(
        ["powershell", "-Command",
         "Get-Process python -ErrorAction SilentlyContinue | "
         "Select-Object Id,CPU,WorkingSet | ConvertTo-Json -Compress"],
        capture_output=True, text=True)
    try:
        return json.loads(r.stdout or "[]")
    except Exception:  # noqa: BLE001
        return []


import json  # noqa: E402

s0 = sheets()
p0 = procs()
print(f"起始: {len(s0)} 张 sheet")
t0 = time.time()
time.sleep(120)
s1 = sheets()
p1 = procs()

new = [f for f in s1 if f not in s0]
print(f"2 分钟后: {len(s1)} 张 sheet，新增 {len(new)}")
for f in new:
    print("  ", time.strftime("%H:%M:%S", time.localtime(f.stat().st_mtime)),
          f.relative_to(root))

# CPU of the worker: is it computing or waiting?
by_id0 = {p["Id"]: p.get("CPU", 0) for p in (p0 if isinstance(p0, list) else [p0])}
by_id1 = {p["Id"]: p.get("CPU", 0) for p in (p1 if isinstance(p1, list) else [p1])}
print()
print("CPU 增量（120 秒内）:")
for pid, c in by_id1.items():
    d = c - by_id0.get(pid, c)
    if abs(d) > 0.05:
        print(f"  PID {pid}: +{d:.1f} 秒  (累计 {c:.0f})")

print()
print("sheet 总数:", len(s1))
print("平均每张间隔: ", end="")
if len(s1) > 1:
    span = s1[-1].stat().st_mtime - s1[0].stat().st_mtime
    print(f"{span / max(len(s1) - 1, 1):.0f} 秒")
else:
    print("（不足两张）")
