"""Does any shot carry the native audio track?"""
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else r"E:\dramakit\projects\短剧_重生恶毒继母")
ffprobe = "ffprobe"

rows = []
for p in sorted(root.rglob("*.mp4")):
    if "tmp" in p.parts:
        continue
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height", "-of", "json", str(p)],
            capture_output=True, text=True, timeout=60)
        info = json.loads(out.stdout or "{}")
    except Exception as e:  # noqa: BLE001
        rows.append((p, f"probe failed: {e}"))
        continue
    kinds = []
    for s in info.get("streams", []):
        kinds.append(f"{s.get('codec_type')}:{s.get('codec_name')}"
                     + (f" {s.get('width')}x{s.get('height')}" if s.get("width") else ""))
    rows.append((p, ", ".join(kinds)))

for p, k in rows:
    rel = p.relative_to(root)
    print(f"{str(rel):<70} {k}")
