"""Are the skill rules at the front of the prompt, where a cache can reuse them?

The stage sends ten thousand characters of rules with every video-prompt
call, and that turns a seven-second call into a thirty-five second one.
MiniMax caches a prompt prefix, so the rules are only free if nothing
varies ahead of them - and the shot description obviously has to. This
reads the template and the call to see the order things are sent in.
"""
import re
from pathlib import Path

out = []

t = Path(r"E:\dramakit\dramakit\prompts\templates.py").read_text(encoding="utf-8")
for name in ("H3_VIDEO_USER", "H3_PROMPT_USER", "IMAGE_PROMPT_USER"):
    i = t.find(name)
    if i < 0:
        continue
    j = t.find('"""', i)
    k = t.find('"""', j + 3)
    body = t[j + 3:k] if j > 0 and k > j else t[i:i + 700]
    out.append(f"=== {name} ===")
    out.append(f"  长度 {len(body):,} 字")
    # where does the constraints/rules placeholder sit?
    for m in re.finditer(r"\{\{?(\w+)\}?\}", body):
        out.append(f"    占位符 {m.group(1)}  在位置 {m.start():>5} / {len(body)}")
    out.append("")

pg = Path(r"E:\dramakit\dramakit\pipeline\promptgen.py").read_text(encoding="utf-8")
i = pg.find("def _gen_h3_prompt")
j = pg.find("\ndef ", i + 10)
out.append("=== _gen_h3_prompt 里怎么拼的 ===")
for n, line in enumerate(pg[i:j].split("\n"), 1):
    if re.search(r"h3_user|constraints|loader|for_stage|complete_json|T\.render", line):
        out.append(f"  {n}: {line.strip()[:150]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\order.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
