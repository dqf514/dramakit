"""The config values that have to agree with the workflow's node ids.

Two of them name a node the file no longer has: the audio slot points at
900, which the converter never created, and the tail frame points at a
video slot that a picture loader was wrongly wired to. Both would reach
the card as a node with no class type, which it refuses outright.

The resolution and frame count matter for the same reason from the other
side - they are what the pipeline writes, and if the config keeps a size
the H3 node cannot take, the render fails on the card rather than here.
"""
from pathlib import Path

out = []

p = Path(r"E:\dramakit\config\default.yaml")
lines = p.read_text(encoding="utf-8").split("\n")

out.append("=== 需要改的行 ===")
for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith("ref_audio_node:"):
        out.append(f"  {i+1}: {line!r}")
    if s.startswith("last_image:"):
        out.append(f"  {i+1}: {line!r}")
    if s.startswith("video_width:") or s.startswith("video_height:"):
        out.append(f"  {i+1}: {line!r}")
    if s.startswith("frames:") or s.startswith("fps:"):
        out.append(f"  {i+1}: {line!r}")
    if s.startswith("native_audio:") or s.startswith("video_references:"):
        out.append(f"  {i+1}: {line!r}")

out.append("")
out.append("=== comfyui 节点映射块 ===")
for i, line in enumerate(lines):
    if line.strip() == "i2v_nodes:":
        for j in range(i, min(i + 12, len(lines))):
            out.append(f"  {j+1}: {lines[j]!r}")
        break

out.append("")
out.append("=== video_width/height 在 config.py 的默认 ===")
c = Path(r"E:\dramakit\dramakit\config.py").read_text(encoding="utf-8")
for n, l in enumerate(c.split("\n"), 1):
    if "video_width" in l or "video_height" in l or "ref_audio_node" in l:
        out.append(f"  {n}: {l.strip()[:120]}")

out.append("")
out.append("=== 新工作流的关键节点 ===")
import json
wf = json.loads(Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
                .read_text(encoding="utf-8"))
for nid, node in wf.items():
    ct = node.get("class_type", "")
    if ct in ("LoadAudio", "LoadImage", "PrimitiveFloat", "PrimitiveInt",
              "ResolutionSelector", "ComfySwitchNode", "PrimitiveBoolean"):
        out.append(f"  #{nid:<5} {ct:<26} {json.dumps(node['inputs'], ensure_ascii=False)[:110]}")
# the audio slot's target
model = next((k for k, n in wf.items()
              if n.get("class_type") == "MiniMaxH3ReferenceToVideo"), None)
if model:
    ins = wf[model]["inputs"]
    out.append("")
    out.append(f"  模型节点 #{model} 的参考槽:")
    for k in sorted(ins):
        if k.startswith("ref_"):
            out.append(f"      {k} -> {ins[k]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\cfgfix.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
