"""Where the audio reference is supposed to come from.

The plumbing is all there - the workflow takes ref_audios, the client
uploads a file and fills the slot, and the config names the node. The one
thing that decides whether a character's voice is used or the model
invents one per clip is what ref is set to, so this reads that decision.
"""
from pathlib import Path
import re

v = Path(r"E:\dramakit\dramakit\pipeline\visual.py").read_text(encoding="utf-8")
out = []

i = v.find('extra["ref_audio_path"]')
if i < 0:
    out.append("  没找到 ref_audio_path")
else:
    # walk back to the enclosing function
    start = v.rfind("\ndef ", 0, i)
    end = v.find("\ndef ", i)
    out.append("=== 所在函数 ===")
    out.append(v[start:end if end > 0 else i + 1500][:1800])

out.append("")
out.append("=== ref 的所有赋值处 ===")
for n, line in enumerate(v.split("\n"), 1):
    if "ref_audio" in line or re.search(r"\bref\s*=", line):
        out.append(f"  {n}: {line.strip()[:130]}")

import re  # noqa: E402

out.append("")
out.append("=== Character 上跟声音有关的字段 ===")
m = Path(r"E:\dramakit\dramakit\models.py").read_text(encoding="utf-8")
for n, line in enumerate(m.split("\n"), 1):
    if any(k in line for k in ("voice", "audio", "lora")) and ":" in line:
        out.append(f"  {n}: {line.strip()[:120]}")

out.append("")
out.append("=== config 里 ref_audio 相关 ===")
c = Path(r"E:\dramakit\dramakit\config.py").read_text(encoding="utf-8")
for n, line in enumerate(c.split("\n"), 1):
    if "ref_audio" in line or "audio" in line.lower() and "ref" in line.lower():
        out.append(f"  {n}: {line.strip()[:130]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\refsrc.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
