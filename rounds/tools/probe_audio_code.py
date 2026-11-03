"""Does the code fill the audio reference, or leave the placeholder?

The workflow accepts a voice - ref_audios points at a LoadAudio node whose
file is still "placeholder.mp3" - so the capability exists. Whether it is
used is a different question: if the client never sets that input, every
clip is generated with a placeholder and the character's voice is whatever
the model invents each time.
"""
import re
from pathlib import Path

out = []
hits = []
for f in Path(r"E:\dramakit\dramakit").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    for n, line in enumerate(t.split("\n"), 1):
        if re.search(r"ref_audio|LoadAudio|placeholder\.mp3|audio_ref|ref_audios",
                     line, re.I):
            hits.append(f"{f.name}:{n}  {line.strip()[:130]}")

out.append("=== 代码里提到音频参考的地方 ===")
out.append("\n".join("  " + h for h in hits) if hits else "  （一处都没有）")

out.append("")
out.append("=== 工作流占位符是怎么替换的 ===")
for f in Path(r"E:\dramakit\dramakit").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    if "placeholder" in t and ("workflow" in t or "prompt" in t):
        for n, line in enumerate(t.split("\n"), 1):
            if "placeholder" in line:
                out.append(f"  {f.name}:{n}  {line.strip()[:130]}")

out.append("")
out.append("=== 当前用的是哪个工作流 ===")
for f in Path(r"E:\dramakit\dramakit").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    if "i2v_minimax" in t or "workflow" in t and "json" in t:
        for n, line in enumerate(t.split("\n"), 1):
            if re.search(r"i2v_|workflow.*json|ref2v", line):
                out.append(f"  {f.name}:{n}  {line.strip()[:140]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\audiocode.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
