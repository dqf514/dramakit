"""What is eating the card?

The render on one of the two 3090s ran out of memory.  The card is
asked, over ssh, what is holding it.
"""
import subprocess
import sys

HOST = "192.168.31.8"
CMDS = [
    "nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv",
    "docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'",
    "nvidia-smi --query-compute-apps=pid,used_memory --format=csv",
]


def sh(cmd):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes",
                        HOST, cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=40)
    return (r.stdout or "") + (r.stderr or "")


for c in CMDS:
    print("=== %s" % c)
    print(sh(c).strip() or "  (没有回答)")
    print()
