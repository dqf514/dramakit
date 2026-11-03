"""What the pipeline sets on a video job, and whether it can read this file.

The config names the nodes it fills - prompt, length, resolution,
references - and the new workflow is a UI export rather than the API shape
the old one was. Both have to be checked: which ids the pipeline writes to,
and whether it can load a file in this form at all.
"""
import json
from pathlib import Path

out = []

# ---- what the config currently maps ------------------------------------
cfg = Path(r"E:\dramakit\config\default.yaml").read_text(encoding="utf-8")
i = cfg.find("i2v_nodes:")
out.append("=== config 的 i2v_nodes ===")
if i > 0:
    out.append(cfg[i:i + 900])
else:
    out.append("  default.yaml 里没有，可能在 config.py 默认值")

# ---- what the code defaults to -----------------------------------------
c = Path(r"E:\dramakit\dramakit\config.py").read_text(encoding="utf-8")
j = c.find("i2v_nodes:")
out.append("")
out.append("=== config.py 的默认 i2v_nodes ===")
out.append(c[j:j + 700] if j > 0 else "  未找到")

# ---- does the loader accept a UI export? -------------------------------
u = Path(r"E:\dramakit\dramakit\providers\comfyui.py").read_text(encoding="utf-8")
out.append("")
out.append("=== 工作流加载 / 格式处理 ===")
for n, line in enumerate(u.split("\n"), 1):
    if any(k in line for k in ("def _pick_workflow", "def _load_workflow",
                               "nodes", "links", "UI 格式", "api 格式",
                               "def validate_workflow")) and ("def " in line or "links" in line or "nodes" in line):
        out.append(f"  {n}: {line.strip()[:130]}")

# ---- the current workflow's own node ids for comparison -----------------
cur = Path(r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v_audio.json")
out.append("")
out.append(f"=== 现用 {cur.name} 的节点 id ===")
d = json.loads(cur.read_text(encoding="utf-8"))
for nid, n in d.items():
    ct = n.get("class_type", "?")
    if any(k in ct for k in ("ReferenceToVideo", "LoadImage", "Primitive",
                             "String", "Float", "Int", "Resolution")):
        ins = n.get("inputs", {})
        keys = [k for k in ins if k not in ("image", "audio")]
        out.append(f"  #{nid:<5} {ct:<34} {keys}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\mapping.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
