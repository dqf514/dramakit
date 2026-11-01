"""Is the stage calling the model, or waiting on something else?

Test calls return in three seconds; the stage has run forty minutes
without finishing sixty of them. That gap is not a slow model, so this
looks at what the server process is actually doing - how many threads,
which connections are open, and whether anything is moving.
"""
import json
import subprocess
import time
from pathlib import Path


def ps(cmd):
    r = subprocess.run(["powershell", "-Command", cmd],
                       capture_output=True, text=True)
    return r.stdout


out = []

out.append("=== python 进程 ===")
out.append(ps(
    "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
    "Where-Object { $_.CommandLine -match 'dj.exe' } | "
    "Select-Object ProcessId,@{n='CPU';e={[math]::Round($_.KernelModeTime/1e7+$_.UserModeTime/1e7,1)}},"
    "@{n='Threads';e={$_.ThreadCount}} | Format-Table -AutoSize | Out-String"))

out.append("=== 到 MiniMax 的连接 ===")
out.append(ps(
    "Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | "
    "Where-Object { $_.RemotePort -in 443,80 } | "
    "Select-Object -First 12 RemoteAddress,RemotePort,OwningProcess | "
    "Format-Table -AutoSize | Out-String"))

# is project.json moving at all?
root = Path(r"E:\dramakit\projects\魔兽世界")
pj = root / "project.json"
m0 = pj.stat().st_mtime
out.append("=== 等 25 秒，看有没有东西在动 ===")
out.append(f"  起始 mtime {time.strftime('%H:%M:%S', time.localtime(m0))}")
time.sleep(25)
m1 = pj.stat().st_mtime
out.append(f"  25 秒后    {time.strftime('%H:%M:%S', time.localtime(m1))}  "
           f"{'有变化' if m1 != m0 else '没变化'}")

recent = sorted(
    ((f.stat().st_mtime, f) for f in root.rglob("*") if f.is_file()
     and time.time() - f.stat().st_mtime < 30),
    reverse=True)
out.append(f"  最近 30 秒内改动的文件: {len(recent)} 个")
for t, f in recent[:6]:
    out.append(f"    {time.strftime('%H:%M:%S', time.localtime(t))} {f.relative_to(root)}")

# CPU again over a window
out.append("")
out.append("=== CPU 增量（20 秒）===")
before = ps("Get-Process python -ErrorAction SilentlyContinue | "
            "Select-Object Id,CPU | ConvertTo-Json -Compress")
time.sleep(20)
after = ps("Get-Process python -ErrorAction SilentlyContinue | "
           "Select-Object Id,CPU | ConvertTo-Json -Compress")
try:
    b = {p["Id"]: p["CPU"] for p in json.loads(before or "[]")}
    a = {p["Id"]: p["CPU"] for p in json.loads(after or "[]")}
    for pid, c in a.items():
        d = c - b.get(pid, c)
        out.append(f"  PID {pid}: +{d:.1f} 秒")
except Exception as e:  # noqa: BLE001
    out.append(f"  解析失败 {e}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\diag.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
