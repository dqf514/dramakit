"""What the first clip looks like, and what it was made from.

The first video of a run is worth looking at closely: it is the one place
where everything comes together at once - the reference sheet, the model
and its adapter, the size, the frame rate and the length - and a mistake
anywhere in that chain shows up as a picture that is wrong in a way no log
line mentions.

So the clip is measured, a frame is taken out of it, and the graph that
produced it is read back from the card to see what it was actually given.
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

out = []
proj = Path(r"E:\dramakit\projects\星际骷髅兵")
vids = sorted((proj / "video").glob("*.mp4"))
out.append(f"=== 视频 {len(vids)} 段 ===")

for v in vids[:3]:
    out.append(f"  {v.name}  {v.stat().st_size/1024:.0f} KB")
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,duration",
             "-of", "json", str(v)],
            capture_output=True, text=True, timeout=60)
        for s in (json.loads(r.stdout or "{}").get("streams") or []):
            out.append(f"      {json.dumps(s, ensure_ascii=False)}")
    except Exception as e:  # noqa: BLE001
        out.append(f"      ffprobe: {e}")

if vids:
    v = vids[0]
    frame = Path(r"C:\Users\David\AppData\Local\Temp\opencode\first_video.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(v),
         "-vf", "select=eq(n\\,10)", "-vframes", "1", str(frame)],
        capture_output=True, timeout=60)
    out.append("")
    out.append(f"  抽帧 -> {frame} ({frame.stat().st_size/1024:.0f} KB)"
               if frame.exists() else "  抽帧失败")

# --- what the card was actually given ----------------------------------
out.append("")
out.append("=== 3090 上这个任务实际用的设置 ===")
with urllib.request.urlopen("http://192.168.31.8:8188/history?max_items=6",
                            timeout=40) as r:
    hist = json.loads(r.read())
for pid, rec in hist.items():
    p = rec.get("prompt")
    g = p[2] if isinstance(p, list) and len(p) > 2 and isinstance(p[2], dict) else {}
    if not g:
        continue
    if not any("ReferenceToVideo" in str(n.get("class_type", "")) for n in g.values()):
        continue
    out.append(f"--- pid {pid[:8]} ---")
    for nid, n in sorted(g.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        ct = str(n.get("class_type", ""))
        ins = n.get("inputs") or {}
        if ct in ("PrimitiveBoolean", "PrimitiveInt", "LoraLoaderModelOnly",
                  "PathchSageAttentionKJ", "MiniMaxH3ReferenceToVideo",
                  "UNETLoader", "CLIPLoader", "VAELoader", "CreateVideo",
                  "RandomNoise", "BasicScheduler", "LoadAudio", "LoadImage"):
            keep = {k: v for k, v in ins.items()
                    if k not in ("prompt", "text")}
            if isinstance(keep.get("prompt"), str):
                keep["prompt"] = keep["prompt"][:90] + "..."
            out.append(f"  #{nid:<5} {ct:<30} {json.dumps(keep, ensure_ascii=False)[:220]}")
    break

Path(r"C:\Users\David\AppData\Local\Temp\opencode\firstvideo.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
