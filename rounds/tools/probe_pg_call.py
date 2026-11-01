"""Why is the stage's model call slower than a test call?

A test call returns in three seconds; the stage has run forty minutes
without finishing sixty of them. Either its prompt is much bigger, or it
asks for far more tokens, or it is not the call that is slow. This reads
what the stage actually sends.
"""
import re
from pathlib import Path

pg = Path(r"E:\dramakit\dramakit\pipeline\promptgen.py").read_text(encoding="utf-8")
out = []

for name in ("_gen_image_prompt", "_gen_h3_prompt", "_gen_score_prompt"):
    i = pg.find(f"def {name}(")
    if i < 0:
        continue
    j = pg.find("\ndef ", i + 10)
    body = pg[i:j if j > 0 else i + 2000]
    out.append(f"=== {name} ===")
    out.append(f"  长度 {len(body)} 字")
    # what it passes to the model
    for n, line in enumerate(body.split("\n"), 1):
        if re.search(r"max_tokens|complete|json_mode|T\.render|for_stage|rules|skills|prompt=", line):
            out.append(f"    {n}: {line.strip()[:150]}")
    out.append("")

# how big are the pieces that go into the prompt
out.append("=== 提示词的组成部分 ===")
for f, keys in [
    (Path(r"E:\dramakit\dramakit\prompts\templates.py"),
     ("IMAGE_PROMPT_USER", "H3_PROMPT_USER", "PROMPTGEN")),
]:
    t = f.read_text(encoding="utf-8", errors="replace")
    for k in keys:
        i = t.find(k)
        if i > 0:
            seg = t[i:i + 400]
            out.append(f"  {k}: 约 {len(seg)} 字起")

out.append("")
sk = Path(r"E:\dramakit\dramakit\skills")
if sk.exists():
    total = sum(f.stat().st_size for f in sk.rglob("*.md"))
    out.append(f"skills/ 文档共 {total:,} 字节（可能整体注入提示词）")

out.append("")
out.append("=== config 里的 max_tokens ===")
cfg = Path(r"E:\dramakit\config\default.yaml").read_text(encoding="utf-8")
for n, line in enumerate(cfg.split("\n"), 1):
    if "max_tokens" in line or "concurrency" in line:
        out.append(f"  {n}: {line.strip()[:100]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\pgcall.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
