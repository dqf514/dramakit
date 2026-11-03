"""Point the node pool at the machine's new address, and turn the second card on.

Both cards are on the same box now, and the pool had one of them disabled
and both pointed at an address that no longer answers. A node that does
not answer is not skipped quietly: the dispatcher tries it, waits for a
timeout, then moves on - so every job pays for the dead address before it
reaches a live one.

The overrides stay as they are. Both instances read one model directory
and both run the same image, so the weights named for the first card are
the weights the second one has too.
"""
import re
import sys
from pathlib import Path

OLD_IP = "192.168.31.7"
NEW_IP = "192.168.31.8"

p = Path(r"E:\dramakit\config\default.yaml")
lines = p.read_text(encoding="utf-8").split("\n")
out = []

ip_hits = 0
for i, line in enumerate(lines):
    if OLD_IP in line:
        lines[i] = line.replace(OLD_IP, NEW_IP)
        ip_hits += 1
out.append(f"  IP 替换 {OLD_IP} -> {NEW_IP}: {ip_hits} 处")

# enable the second node: find its `enabled:` line within its block
in_b = False
for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith("- name:") and "gpu3090-b" in s:
        in_b = True
        continue
    if in_b and s.startswith("enabled:"):
        if "False" in s or "false" in s:
            indent = line[: len(line) - len(line.lstrip())]
            comment = ""
            m = re.search(r"\s{2,}#.*$", line)
            if m:
                comment = "  " + m.group(0).strip()
            lines[i] = f"{indent}enabled: True{comment}"
            out.append(f"  gpu3090-b enabled: False -> True")
        else:
            out.append(f"  gpu3090-b 已经是 True")
        in_b = False

p.write_text("\n".join(lines), encoding="utf-8")

# --- verify ------------------------------------------------------------
import yaml   # noqa: E402
d = yaml.safe_load(p.read_text(encoding="utf-8"))
c = d["comfyui"]
out.append("")
out.append("=== 改后 comfyui.nodes ===")
import json   # noqa: E402
for n in c.get("nodes") or []:
    out.append(f"  {n.get('name'):14} enabled={n.get('enabled')}  "
               f"roles={n.get('roles')}  {n.get('base_url')}")
    out.append(f"      ssh={n.get('ssh_host')}@{n.get('ssh_user')}  "
               f"remote_models={n.get('remote_models')}")
    out.append("      overrides="
               + json.dumps(n.get("graph_overrides") or {}, ensure_ascii=False)[:160])
out.append("")
out.append("=== Config.load ===")
sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config   # noqa: E402
cfg = Config.load(Config.discover())
for n in cfg.comfyui.nodes:
    out.append(f"  {n.name:14} enabled={n.enabled} {n.base_url} roles={n.roles}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\nodes_ip.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
