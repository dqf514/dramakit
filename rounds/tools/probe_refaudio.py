"""What the code decides to hand the model as a character's voice.

There is a function whose whole job is to pick an audio reference for a
shot, and the model takes three of them. What it returns decides whether
a character sounds like themselves across clips or like whatever the model
invents each time - so its logic is the answer to whether the proposed
voice samples would be used.
"""
import re
from pathlib import Path

v = Path(r"E:\dramakit\dramakit\pipeline\visual.py").read_text(encoding="utf-8")
out = []

i = v.find("def _reference_audio")
if i < 0:
    # maybe it lives elsewhere
    for f in Path(r"E:\dramakit\dramakit").rglob("*.py"):
        t = f.read_text(encoding="utf-8", errors="replace")
        if "def _reference_audio" in t:
            i = t.find("def _reference_audio")
            v = t
            out.append(f"  定义在 {f.name}")
            break

if i >= 0:
    j = v.find("\ndef ", i + 10)
    out.append("=== _reference_audio ===")
    out.append(v[i:j if j > 0 else i + 1800])
else:
    out.append("  没找到 _reference_audio 的定义")

out.append("")
out.append("=== picture_plan 里的角色/声音顺序 ===")
for f in Path(r"E:\dramakit\dramakit\pipeline").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    if "def picture_plan" in t:
        i = t.find("def picture_plan")
        j = t.find("\ndef ", i + 10)
        body = t[i:j if j > 0 else i + 2200]
        out.append(f"  在 {f.name}")
        for n, line in enumerate(body.split("\n"), 1):
            if re.search(r"audio|voice|role|kind|ref", line, re.I):
                out.append(f"    {n}: {line.strip()[:130]}")

out.append("")
out.append("=== 角色库有没有生成过声音文件 ===")
root = Path(r"E:\dramakit\projects\魔兽世界\characters")
if root.exists():
    audio = [f for f in root.rglob("*") if f.suffix.lower() in (".mp3", ".wav", ".m4a", ".flac")]
    out.append(f"  声音文件 {len(audio)} 个")
    for f in audio[:10]:
        out.append(f"    {f.relative_to(root)}  {f.stat().st_size // 1024} KB")
else:
    out.append("  角色目录不存在")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\refaudio.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
