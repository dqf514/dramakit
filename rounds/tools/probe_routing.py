"""Which machine draws the still, and which renders the clip?

The picture stage does the stills first and the clips after, with a comment
saying one GPU cannot hold both models. That is true of one GPU. If the
two go to different machines - a local card for stills and a remote one for
video - then the ordering buys nothing and costs the whole idle window:
the machine that renders waits while the machine that draws finishes a
batch it does not need to finish first.
"""
import json
import re
from pathlib import Path

out = []

c = Path(r"E:\dramakit\config\default.yaml").read_text(encoding="utf-8")
out.append("=== comfyui 节点配置 ===")
grab = False
for line in c.split("\n"):
    if line.strip().startswith("nodes:"):
        grab = True
    if grab:
        if line and not line.startswith((" ", "#")) and not line.strip().startswith("nodes:"):
            break
        if line.strip():
            out.append("  " + line.rstrip()[:110])

out.append("")
out.append("=== 代码里怎么选端点 ===")
for f in Path(r"E:\dramakit\dramakit").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    for n, line in enumerate(t.split("\n"), 1):
        if re.search(r"nodes_from_config|pick_node|node_for|kind == \"video\"|kind == \"image\"|endpoint", line):
            out.append(f"  {f.name}:{n}  {line.strip()[:130]}")

out.append("")
out.append("=== visual 里出图/出视频分别怎么调 ===")
v = Path(r"E:\dramakit\dramakit\pipeline\visual.py").read_text(encoding="utf-8")
for n, line in enumerate(v.split("\n"), 1):
    if re.search(r"generate_image|generate_video|vis\.(image|video)|_gen_image|_gen_video", line):
        out.append(f"  {n}: {line.strip()[:130]}")

out.append("")
out.append("=== 两阶段注释 ===")
i = v.find("Two phases on purpose")
if i > 0:
    out.append(v[i - 20:i + 520])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\routing.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
