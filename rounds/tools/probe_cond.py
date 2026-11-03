"""What the fast old clips were given that the new ones are not, and the
other way round.

Eight steps with the LoRA now costs fifteen minutes where the same setup
in the old workflow cost eleven. Nothing about the sampler explains that
- the settings match - so it has to be the conditioning: how many
pictures went in to be encoded, whether a voice went with them, and which
attention mode was asked for.

Each job is read for those, and the two groups are put side by side.
"""
import json
import sys
import urllib.request
from pathlib import Path

CARD = "http://192.168.31.7:8188"
out = []

with urllib.request.urlopen(CARD + "/history?max_items=60", timeout=40) as r:
    hist = json.loads(r.read())


def graph_of(rec):
    p = rec.get("prompt")
    return p[2] if isinstance(p, list) and len(p) > 2 and isinstance(p[2], dict) else {}


def dur(rec):
    t0 = t1 = None
    for m in (rec.get("status") or {}).get("messages") or []:
        if isinstance(m, list) and len(m) >= 2:
            k, d = m[0], m[1] or {}
            if k == "execution_start":
                t0 = d.get("timestamp")
            elif k in ("execution_success", "execution_error",
                       "execution_interrupted"):
                t1 = d.get("timestamp")
    return (t1 - t0) / 1000.0 if (t0 and t1) else 0.0


rows = []
for pid, rec in hist.items():
    g = graph_of(rec)
    if not g:
        continue
    secs = dur(rec)
    if secs <= 0:
        continue
    imgs = auds = 0
    frames = None
    sage = None
    steps = None
    for n in g.values():
        ins = n.get("inputs") or {}
        ct = str(n.get("class_type", ""))
        if "ReferenceToVideo" in ct:
            imgs = len([k for k in ins if k.startswith("ref_images.")])
            auds = len([k for k in ins if k.startswith("ref_audios.")])
            v = ins.get("length")
            if isinstance(v, (int, float)):
                frames = v
        if "SageAttention" in ct:
            sage = ins.get("sage_attention")
        if ct == "BasicScheduler":
            s = ins.get("steps")
            if isinstance(s, (int, float)):
                steps = s
            elif isinstance(s, list):
                src = g.get(str(s[0])) or {}
                steps = (src.get("inputs") or {}).get("value")
    if not frames:
        continue
    rows.append({"pid": pid[:8], "min": secs / 60, "frames": frames,
                 "s": secs / frames, "imgs": imgs, "auds": auds,
                 "sage": sage, "steps": steps,
                 "wf": "新" if len(g) >= 30 else "旧"})

rows.sort(key=lambda r: (r["wf"], r["frames"]))
out.append(f"{'wf':3} {'pid':9} {'分钟':>6} {'帧':>5} {'每帧s':>6} "
           f"{'参考图':>5} {'音频':>4} {'步数':>5}  attention")
for r in rows:
    out.append(f"{r['wf']:3} {r['pid']:9} {r['min']:6.1f} {r['frames']:5} "
               f"{r['s']:6.1f} {r['imgs']:5} {r['auds']:4} "
               f"{str(r['steps']):>5}  {r['sage']}")

# --- group by workflow, only comparable frame counts -------------------
out.append("")
out.append("=== 只看 243 帧附近的（可比）===")
band = [r for r in rows if 230 <= r["frames"] <= 260]
for wf in ("旧", "新"):
    g = [r for r in band if r["wf"] == wf]
    if not g:
        out.append(f"  {wf}: 无")
        continue
    avg_s = sum(r["s"] for r in g) / len(g)
    avg_i = sum(r["imgs"] for r in g) / len(g)
    avg_a = sum(r["auds"] for r in g) / len(g)
    out.append(f"  {wf}: {len(g)} 次，平均 {avg_s:.1f}s/帧，"
               f"参考图 {avg_i:.1f}，音频 {avg_a:.1f}")

out.append("")
out.append("=== 按参考图数量分组（新工作流）===")
new = [r for r in rows if r["wf"] == "新"]
for n in sorted({r["imgs"] for r in new}):
    g = [r for r in new if r["imgs"] == n]
    if len(g) < 2:
        continue
    out.append(f"  {n} 张参考图: {len(g)} 次，"
               f"{sum(r['s'] for r in g)/len(g):.1f}s/帧")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\cond.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
