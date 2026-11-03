"""Where the switch sits, and what the scheduler is told to do.

The LoRA feeds a switch whose output nothing reads, while the sampler takes
its model straight from the loader - so as the file stands the 8-step LoRA
is loaded and unused. Whether that is how the card runs it or a link the
conversion dropped decides the step count, and a scheduler told 8 steps on
a model that never saw the LoRA is a different render than the author's.
"""
import json
from pathlib import Path

ui = json.loads(Path(r"D:\Downloads\短剧专用.json").read_text(encoding="utf-8"))
api = json.loads(Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
                 .read_text(encoding="utf-8"))
nodes = {str(n.get("id")): n for n in ui.get("nodes", [])}
links = {str(r[0]): r for r in (ui.get("links") or []) if isinstance(r, list)}

out = []


def show(nid: str, label: str) -> None:
    n = nodes.get(nid)
    if not n:
        out.append(f"  #{nid} {label}: 原文件里没有")
        return
    out.append(f"  #{nid} {label} ({n.get('type')})")
    out.append(f"      widgets: {json.dumps(n.get('widgets_values'), ensure_ascii=False)[:130]}")
    for inp in n.get("inputs") or []:
        lid = inp.get("link")
        row = links.get(str(lid)) if lid is not None else None
        src = f"来自 #{row[1]}[{row[2]}]" if row else ("未连接" if lid is None else "?")
        out.append(f"      输入 {inp.get('name')}: {src}")
    # outputs
    for oi, o in enumerate(n.get("outputs") or []):
        lids = o.get("links") or []
        dst = []
        for l in lids:
            row = links.get(str(l))
            if row:
                dst.append(f"#{row[3]}[{row[4]}]")
        out.append(f"      输出[{oi}] {o.get('name')} -> {', '.join(dst) or '（无）'}")


out.append("=== 开关 #141 ===")
show("141", "ComfySwitchNode")
out.append("")
out.append("=== LoRA #145 ===")
show("145", "LoraLoaderModelOnly")
out.append("")
out.append("=== SageAttention #151 ===")
show("151", "PathchSageAttentionKJ")
out.append("")
out.append("=== UNET #127 ===")
show("127", "UNETLoader")
out.append("")
out.append("=== 步数来源 ===")
show("142", "PrimitiveInt/Float")
show("124", "BasicScheduler")
out.append("")
out.append("=== 采样 #125 / 引导 #126 ===")
show("126", "BasicGuider")
show("125", "SamplerCustomAdvanced")

# ---- so: does the sampler's model path pass through the LoRA? ----------
out.append("")
out.append("=== 结论：采样器的 model 从哪来 ===")
sched = nodes.get("124") or {}
for inp in sched.get("inputs") or []:
    if inp.get("name") == "model":
        lid = str(inp.get("link"))
        row = links.get(lid)
        if row:
            out.append(f"  BasicScheduler.model <- #{row[1]} ({nodes.get(str(row[1]), {}).get('type')})")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\switch.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
