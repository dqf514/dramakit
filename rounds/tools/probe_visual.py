"""What the picture stage needs, and what is already waiting for it.

The 3090 is idle at zero percent while the pipeline writes text, and three
episodes already have their prompts. If the stages are strictly ordered,
the machine that renders waits on the machine that writes - which is the
opposite of the division the flow describes, where the stills machine and
the video machine run side by side. This reads what visual actually
requires per shot, and what those three episodes already have.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []

v = Path(r"E:\dramakit\dramakit\pipeline\visual.py").read_text(encoding="utf-8")
out.append("=== visual.run 的开头 ===")
i = v.find("def run(")
out.append(v[i:i + 1500])

out.append("")
out.append("=== visual 里跳过已完成的判断 ===")
for n, line in enumerate(v.split("\n"), 1):
    if re.search(r"skip|DONE|status ==|已生成|if .*prompt", line):
        out.append(f"  {n}: {line.strip()[:130]}")

out.append("")
out.append("=== runner 的阶段顺序 ===")
r = Path(r"E:\dramakit\dramakit\pipeline\runner.py").read_text(encoding="utf-8")
m = re.search(r"ORDER\s*=\s*\[(.*?)\]", r, re.S)
out.append("  " + (m.group(0).replace("\n", " ") if m else "未找到"))

out.append("")
out.append("=== 那 3 集现在有什么 ===")
d = json.loads(Path(r"E:\dramakit\projects\魔兽世界\project.json")
               .read_text(encoding="utf-8"))
for e in (d.get("episodes") or [])[:4]:
    shots = [sh for sc in e.get("scenes", []) for sh in sc.get("shots", [])]
    with_prompt = sum(1 for sh in shots if sh.get("prompt"))
    with_h3 = sum(1 for sh in shots if sh.get("video_prompt"))
    with_img = sum(1 for sh in shots if sh.get("image_path"))
    with_vid = sum(1 for sh in shots if sh.get("video_path"))
    ss = e.get("stage_status", {})
    out.append(f"  第{e.get('index')}集: {len(shots)} 镜  "
               f"提示词 {with_prompt}  H3 {with_h3}  首帧 {with_img}  视频 {with_vid}  "
               f"阶段 {json.dumps(ss, ensure_ascii=False)}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\visual.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
