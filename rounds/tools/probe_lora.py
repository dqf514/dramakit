"""Two things the validation could not settle: the notes, and the LoRA.

Three note nodes are not on the card, and a /prompt that names a class the
server does not have is rejected outright - the whole render fails, not
just the note. And the LoRA node loads a model that nothing reads: the
sampler takes its model from the attention patch, which takes it straight
from the loader, so the LoRA is a leaf. Whether that is how the file was
built or a link that the conversion lost is the difference between an
8-step render and a full-length one.
"""
import json
from pathlib import Path

out = []

# ---------- the file as exported, and the file we ship -------------------
ui = json.loads(Path(r"D:\Downloads\短剧专用.json").read_text(encoding="utf-8"))
api = json.loads(Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
                 .read_text(encoding="utf-8"))

# ---------- 1. what the notes are, and whether anything reads them -------
out.append("=== MarkdownNote 节点：有谁连着它们吗 ===")
note_ids = {str(n.get("id")) for n in ui.get("nodes", [])
            if n.get("type") == "MarkdownNote"}
out.append(f"  UI 文件里的 note 节点: {sorted(note_ids, key=int)}")
links = ui.get("links", []) or []
touched = [row for row in links
           if isinstance(row, list) and (str(row[1]) in note_ids or str(row[3]) in note_ids)]
out.append(f"  有连线涉及 note 的: {len(touched)} 条")
for row in touched[:6]:
    out.append(f"    {row}")

# does any node in the api graph point at a note?
read_by = [f"#{nid}({n.get('class_type')})"
           for nid, n in api.items()
           for v in (n.get("inputs") or {}).values()
           if isinstance(v, list) and str(v[0]) in note_ids]
out.append(f"  谁在读 note: {read_by or '（无 —— 纯注释）'}")

# ---------- 2. the LoRA: was it wired in the original? -------------------
out.append("")
out.append("=== 原 UI 文件里 LoRA(#145) 的接线 ===")
for row in links:
    if isinstance(row, list) and len(row) >= 5:
        lid, frm, fslot, to, tslot = row[:5]
        if str(frm) == "145" or str(to) == "145":
            out.append(f"  link {lid}: #{frm}[{fslot}] -> #{to}[{tslot}]")

# who does 145 feed, and where does 151 take its model from
out.append("")
out.append("=== 转换后：谁消费 LoRA / SageAttention ===")
for target in ("145", "151", "127"):
    readers = [f"#{nid}.{k}({n.get('class_type')})"
               for nid, n in api.items()
               for k, v in (n.get("inputs") or {}).items()
               if isinstance(v, list) and str(v[0]) == target]
    out.append(f"  #{target} 的输出被谁读: {readers or '（无 —— 是叶子）'}")

# ---------- 3. does the card reject an unknown class_type? ---------------
out.append("")
out.append("=== 原文件里 SageAttention 节点存在吗（UI 侧） ===")
for n in ui.get("nodes", []):
    if n.get("type") in ("PathchSageAttentionKJ", "LoraLoaderModelOnly",
                         "UNETLoader"):
        out.append(f"  #{n.get('id')} {n.get('type')} "
                   f"widgets={json.dumps(n.get('widgets_values'), ensure_ascii=False)[:120]}")

# ---------- 4. output chain: sampler -> decode -> video -> save ---------
out.append("")
out.append("=== 输出链路 ===")
for nid in ("125", "122", "121", "130", "92", "152", "153"):
    n = api.get(nid)
    if n:
        ins = n.get("inputs", {})
        wires = {k: v for k, v in ins.items() if isinstance(v, list)}
        out.append(f"  #{nid:<5} {n.get('class_type'):<26} {json.dumps(wires, ensure_ascii=False)[:130]}")

# every node and whether its output is read by anyone
out.append("")
out.append("=== 每个节点的输出是否有人读（叶子=输出丢失）===")
for nid, n in api.items():
    readers = [a for a, m in api.items()
               for v in (m.get("inputs") or {}).values()
               if isinstance(v, list) and str(v[0]) == nid]
    if not readers:
        out.append(f"  #{nid:<5} {n.get('class_type'):<32} ← 没人读")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\lora.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
