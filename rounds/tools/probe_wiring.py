"""Is the audio reference wired to the model, or left dangling?

The workflow loads an audio file and the model has an audio VAE, but the
node that takes the reference may not be connected to the node that makes
the video. If it is not, then handing the model a character's voice is a
workflow edit rather than a code change, and the difference matters for
what has to be built.
"""
import json
from pathlib import Path

p = Path(r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v_audio.json")
data = json.loads(p.read_text(encoding="utf-8"))

out = []
# build the link map: who consumes node X output 0
consumers: dict[str, list[str]] = {}
for nid, node in data.items():
    for key, val in (node.get("inputs") or {}).items():
        if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str):
            src = str(val[0])
            consumers.setdefault(src, []).append(f"节点{nid}.{key}")

out.append("=== LoadAudio(900) 的输出被谁消费 ===")
out.append("  " + (", ".join(consumers.get("900", [])) or "（没有人用——孤立节点）"))

out.append("")
out.append("=== 节点 104 的全部输入 ===")
n104 = data.get("104", {})
for k, v in (n104.get("inputs") or {}).items():
    if k == "ref_images":
        out.append(f"  {k}: {len(v)} 个槽位")
    else:
        out.append(f"  {k}: {json.dumps(v, ensure_ascii=False)[:90]}")

out.append("")
out.append("=== 全部节点及其被谁用 ===")
for nid in sorted(data, key=lambda x: int(x) if x.isdigit() else 0):
    node = data[nid]
    ct = node.get("class_type", "?")
    used = consumers.get(nid, [])
    out.append(f"  节点 {nid:<5} {ct:<34} 被 {', '.join(used) if used else '（无人使用）'}")

out.append("")
out.append("=== 是否有音频进入模型 ===")
audio_into_model = False
for nid, node in data.items():
    ct = node.get("class_type", "")
    if "ReferenceToVideo" in ct or "H3" in ct:
        for k, v in (node.get("inputs") or {}).items():
            if isinstance(v, list) and str(v[0]) == "900":
                audio_into_model = True
                out.append(f"  节点 {nid} 的 {k} 来自 LoadAudio")
if not audio_into_model:
    out.append("  没有：模型节点没有接收 LoadAudio 的输入")
    out.append("  （audio_vae 是模型自己解码生成的音频用的，不是参考输入）")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\wiring.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
