"""Which node takes the voice, and what the pipeline sends to it.

The audio-ref workflow mentions audio more often than the one without it,
so a voice input exists. This prints those nodes, and then what the code
actually fills in when it builds the request - because a workflow that
accepts an audio reference is only useful if something hands it one.
"""
import json
from pathlib import Path

out = []

p = Path(r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v_audio.json")
data = json.loads(p.read_text(encoding="utf-8"))

out.append("=== 含 audio 的节点 ===")
for nid, node in data.items():
    blob = json.dumps(node, ensure_ascii=False)
    if "audio" in blob.lower() or "mp3" in blob.lower():
        out.append(f"  节点 {nid}:")
        out.append("    " + json.dumps(node, ensure_ascii=False)[:420])
        out.append("")

# and how it differs from the workflow without audio
q = Path(r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v.json")
d2 = json.loads(q.read_text(encoding="utf-8"))
only = set(data) - set(d2)
out.append("=== audio 版独有/不同的节点 ===")
for nid in sorted(only, key=lambda x: int(x) if x.isdigit() else 0):
    out.append(f"  节点 {nid}: {json.dumps(data[nid], ensure_ascii=False)[:300]}")
for nid in sorted(set(data) & set(d2), key=lambda x: int(x) if x.isdigit() else 0):
    if data[nid] != d2[nid]:
        out.append(f"  改动 {nid}:")
        out.append(f"    audio 版: {json.dumps(data[nid], ensure_ascii=False)[:260]}")
        out.append(f"    无音频版: {json.dumps(d2[nid], ensure_ascii=False)[:260]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\audionode.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
