"""What the video workflow's inputs actually are.

The audio-ref workflow is the one file that would settle whether a voice
can be handed to the model as a reference. It parsed as zero nodes, so
the shape is not what was assumed - this prints what is really in it.
"""
import json
from pathlib import Path

out = []
for name in ("i2v_minimax_h3_ref2v_audio.json", "i2v_minimax_h3_ref2v.json",
             "i2v_minimax_h3.json"):
    p = Path(r"E:\dramakit\config\comfyui") / name
    out.append(f"=== {name} ===")
    if not p.exists():
        out.append("  不存在")
        out.append("")
        continue
    raw = p.read_text(encoding="utf-8")
    out.append(f"  {len(raw):,} 字节")
    try:
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        out.append(f"  JSON 解析失败: {e}")
        out.append("")
        continue
    out.append(f"  顶层类型: {type(data).__name__}, "
               f"键: {list(data)[:12] if isinstance(data, dict) else len(data)}")
    # find anything that looks like a node and anything that looks like audio
    blob = json.dumps(data, ensure_ascii=False)
    for kw in ("audio", "Audio", "voice", "speech", "sound", "wav", "mp3"):
        n = blob.count(kw)
        if n:
            out.append(f"    含 '{kw}': {n} 次")
    # node list, whichever key holds it
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                out.append(f"  列表键 {k}: {len(v)} 项, 首项键 {list(v[0])[:8]}")
    out.append("")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\wfblob.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
