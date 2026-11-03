"""Can the video model take a voice as a reference, and where does voice come from now?

The idea is to take the voice a character has in the first clip they speak
in and hand it back as that character's reference for every clip after, so
the same person sounds the same throughout. That needs the model to accept
an audio input. This reads the workflow that is actually sent, and the two
places voice is produced today - the TTS stage and the model's own audio.
"""
import json
from pathlib import Path

out = []

wf = Path(r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v_audio.json")
out.append(f"=== {wf.name} ===")
if wf.exists():
    data = json.loads(wf.read_text(encoding="utf-8"))
    out.append(f"  节点数 {len(data.get('nodes', []))}")
    for n in data.get("nodes", []):
        t = n.get("type", "")
        title = n.get("title", "")
        if any(k in (t + title).lower() for k in
               ("audio", "sound", "voice", "speech", "loadaudio", "ref")):
            out.append(f"    #{n.get('id')} {t}  {title}")
    # every input slot name, so an audio slot cannot hide
    out.append("  --- 全部节点类型 ---")
    types = sorted({n.get("type", "?") for n in data.get("nodes", [])})
    out.append("    " + ", ".join(types))
else:
    out.append("  不存在")

out.append("")
wf2 = Path(r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v.json")
out.append(f"=== {wf2.name}（无 audio 的那个）===")
if wf2.exists():
    d2 = json.loads(wf2.read_text(encoding="utf-8"))
    types = sorted({n.get("type", "?") for n in d2.get("nodes", [])})
    out.append("    " + ", ".join(types))

out.append("")
out.append("=== voice 阶段做了什么 ===")
v = Path(r"E:\dramakit\dramakit\pipeline\voice.py").read_text(encoding="utf-8")
i = v.find("def run(")
out.append(v[i:i + 1200])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\voiceref.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
