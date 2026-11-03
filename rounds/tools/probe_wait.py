"""How much rendering is waiting, and what an idle hour costs.

Three episodes have every prompt they need and the 3090 is at zero percent.
The stages are ordered so the machine that writes text finishes before the
machine that draws begins - the opposite of the division the flow
describes. This puts the waiting work in hours.
"""
import json
import re
from pathlib import Path

out = []

c = Path(r"E:\dramakit\config\default.yaml").read_text(encoding="utf-8")
out.append("=== 出图/出视频配置 ===")
grab = False
for n, line in enumerate(c.split("\n"), 1):
    if line.strip().startswith("comfyui:"):
        grab = True
    if grab:
        if n > 1 and line and not line.startswith((" ", "#")) and not line.strip().startswith("comfyui:"):
            grab = False
            continue
        if any(k in line for k in ("width", "height", "mode", "concurrency",
                                   "video_concurrency", "steps", "max_video",
                                   "base_url", "enabled", "ref_image")):
            out.append(f"  {line.strip()[:110]}")

out.append("")
out.append("=== 等待中的工作量 ===")
d = json.loads(Path(r"E:\dramakit\projects\魔兽世界\project.json")
               .read_text(encoding="utf-8"))
eps = d.get("episodes") or []
ready_shots = 0
all_shots = 0
for e in eps:
    shots = [sh for sc in e.get("scenes", []) for sh in sc.get("shots", [])]
    all_shots += len(shots)
    ready_shots += sum(1 for sh in shots
                       if sh.get("prompt") and sh.get("video_prompt"))
out.append(f"  总镜头 {all_shots}，已具备出片条件 {ready_shots}")
out.append(f"  未具备 {all_shots - ready_shots}")

# measured: 19.3 min for a 768p clip on one 3090
mins = 19.3
out.append("")
out.append(f"  按实测 19.3 分钟/段（单卡 3090，768p）:")
out.append(f"    已就绪的 {ready_shots} 段 → {ready_shots * mins / 60:.1f} 小时")
out.append(f"    全部 {all_shots} 段 → {all_shots * mins / 60:.1f} 小时"
           f"（{all_shots * mins / 60 / 24:.1f} 天）")

out.append("")
out.append("=== 阶段顺序（问题所在）===")
r = Path(r"E:\dramakit\dramakit\pipeline\runner.py").read_text(encoding="utf-8")
m = re.search(r"ORDER\s*=\s*\[(.*?)\]", r, re.S)
out.append("  " + (m.group(0).replace("\n", " ") if m else "?"))
out.append("")
out.append("  runner 是 stage-major：先把一个阶段在所有集上做完，再进下一阶段。")
out.append("  所以 visual 要等 promptgen 的全部 9 集写完才开始，")
out.append("  而 visual 内部本来就支持逐镜跳过（已 DONE 的镜头跳过）。")

out.append("")
out.append("=== visual 内部的并行意图 ===")
v = Path(r"E:\dramakit\dramakit\pipeline\visual.py").read_text(encoding="utf-8")
for n, line in enumerate(v.split("\n")[:20], 1):
    if any(k in line for k in ("并行", "parallel", "同时", "side by side", "5080", "3090")):
        out.append(f"  {n}: {line.strip()[:120]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\wait.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
