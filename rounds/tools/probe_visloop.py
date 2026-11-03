"""Does the picture stage batch the stills before the clips, or pair them?

The config says image_then_video, which could mean every still first and
then every clip - so even an early start would leave the 3090 waiting on
the 5080 for the whole batch - or one shot's still then that shot's clip,
which pipelines them. The loop decides which, and so decides what a fix
has to change.
"""
from pathlib import Path

v = Path(r"E:\dramakit\dramakit\pipeline\visual.py").read_text(encoding="utf-8")
out = []

i = v.find("def run(")
body = v[i:v.find("\ndef ", i + 10) if v.find("\ndef ", i + 10) > 0 else i + 4000]
out.append("=== visual.run 全文 ===")
out.append(body[:4000])
out.append("")

# the actual generation entry points
for name in ("_gen_image", "_gen_video", "generate_image", "generate_video",
             "image_then_video"):
    for n, line in enumerate(v.split("\n"), 1):
        if name in line and ("def " in line or "mode" in line):
            out.append(f"  {n}: {line.strip()[:130]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\visloop.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
