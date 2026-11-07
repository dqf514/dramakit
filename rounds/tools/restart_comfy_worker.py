"""Restart the worker that ran out of memory.

The card holds what the last render left in it: the model, the cached
blocks, the allocator's memory.  A container that has been up for nine
hours and a render that asks for one more gigabyte is the end of it.
"""
import subprocess
import sys

HOST = "192.168.31.8"
NAME = sys.argv[1] if len(sys.argv) > 1 else "comfyui-h3-a"


def sh(cmd, timeout=120):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes",
                        HOST, cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout or "").strip() or (r.stderr or "").strip()


print("  重启前：", sh("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader"))
print("  %s：%s" % (NAME, sh("docker restart %s" % NAME, timeout=180)))
print("  等它起来……")
for port in (8188, 8189):
    ok = ""
    for _ in range(30):
        ok = sh("curl -s --max-time 5 http://127.0.0.1:%d/system_stats | "
                "head -c 60" % port, timeout=30)
        if ok:
            break
        import time
        time.sleep(6)
    print("  %d：%s" % (port, "起来了" if ok else "没起来"))
print("  重启后：", sh("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader"))
