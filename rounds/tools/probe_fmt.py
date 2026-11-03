"""Can the loader read a workflow exported from the web UI?

The new file is a UI export - a nodes array with links - while the one
the config points at is the API form, a map of id to node. The pipeline
sends a workflow to /prompt, which takes the API form, so either the
loader converts or the file has to be converted first. This reads what
the loader assumes.
"""
import re
from pathlib import Path

out = []

n = Path(r"E:\dramakit\dramakit\providers\nodes.py").read_text(encoding="utf-8")
m = re.search(r"def infer_workflow\(.*?(?=\ndef |\Z)", n, re.S)
out.append("=== infer_workflow ===")
out.append(m.group(0)[:1400] if m else "  未找到")

out.append("")
out.append("=== 代码里对 UI 格式（nodes 数组 / links）的处理 ===")
found = False
for f in Path(r"E:\dramakit\dramakit").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(t.split("\n"), 1):
        if re.search(r'"nodes"|\'nodes\'|\.get\("links"\)|"links"', line):
            out.append(f"  {f.name}:{i}  {line.strip()[:130]}")
            found = True
if not found:
    out.append("  （一处都没有 —— 不处理 UI 格式）")

out.append("")
out.append("=== 提交到 ComfyUI 用的是什么 ===")
u = Path(r"E:\dramakit\dramakit\providers\comfyui.py").read_text(encoding="utf-8")
for i, line in enumerate(u.split("\n"), 1):
    if re.search(r'"/prompt"|/prompt|def generate_video|def submit', line):
        out.append(f"  {i}: {line.strip()[:130]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\fmt.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
