"""How long a clip takes, against the settings it was sent with.

The card keeps every job it has run, with the settings it ran at and the
times it started and finished. Two settings matter here: how many steps
the sampler took, and whether the turbo LoRA was in the path - the
workflow switches between twenty steps on the bare model and four with
the LoRA, and only one of those can be the fast one.

So each job is read for its steps, its switch, and its duration, and the
two groups are put side by side. That answers whether the slow clips are
the ones without the LoRA, rather than guessing at it from a stopwatch.
"""
import json
import sys
import urllib.request
from pathlib import Path

CARD = "http://192.168.31.7:8188"
out = []


def get(path, timeout=40):
    with urllib.request.urlopen(CARD + path, timeout=timeout) as r:
        return json.loads(r.read())


hist = get("/history?max_items=60")
out.append(f"=== 3090 最近 {len(hist)} 条执行 ===")
out.append("")

rows = []
for pid, rec in hist.items():
    p = rec.get("prompt")
    graph = p[2] if isinstance(p, list) and len(p) > 2 and isinstance(p[2], dict) else {}
    if not graph:
        continue
    msgs = (rec.get("status") or {}).get("messages") or []
    t0 = t1 = None
    for m in msgs:
        if not (isinstance(m, list) and len(m) >= 2):
            continue
        kind, data = m[0], m[1] or {}
        ts = data.get("timestamp")
        if kind == "execution_start" and ts:
            t0 = ts
        elif kind in ("execution_success", "execution_error", "execution_interrupted") and ts:
            t1 = ts
    if not (t0 and t1):
        continue
    secs = (t1 - t0) / 1000.0

    # the settings that decide the cost
    steps = None
    switch = None
    lora = None
    frames = None
    w = h = None
    for nid, node in graph.items():
        ct = str(node.get("class_type", ""))
        ins = node.get("inputs") or {}
        if ct == "PrimitiveBoolean":
            switch = ins.get("value")
        if ct == "PrimitiveInt":
            steps = ins.get("value")          # the switch picks one of these
        if ct == "LoraLoaderModelOnly":
            lora = ins.get("lora_name")
        if ct == "MiniMaxH3ReferenceToVideo":
            raw_len = ins.get("length")
            # it can be a literal or a wire from the duration calculator;
            # a wire has to be followed to know what the sampler was told
            if isinstance(raw_len, list) and raw_len:
                src = graph.get(str(raw_len[0])) or {}
                raw_len = (src.get("inputs") or {}).get("value")
                if raw_len is None:
                    raw_len = (src.get("inputs") or {}).get("expression")
            frames = raw_len
            w, h = ins.get("width"), ins.get("height")
    # which step value the switch actually selected
    chosen = None
    for nid, node in graph.items():
        if node.get("class_type") == "ComfySwitchNode":
            ins = node.get("inputs") or {}
            on_false = ins.get("on_false")
            on_true = ins.get("on_true")
            if isinstance(on_false, list) and isinstance(on_true, list):
                src = on_true if switch else on_false
                srcnode = graph.get(str(src[0])) or {}
                if srcnode.get("class_type") == "PrimitiveInt":
                    chosen = (srcnode.get("inputs") or {}).get("value")
    # whether the model path goes through the LoRA
    through_lora = False
    for nid, node in graph.items():
        if "SageAttention" in str(node.get("class_type", "")):
            m = (node.get("inputs") or {}).get("model")
            if isinstance(m, list):
                sw = graph.get(str(m[0])) or {}
                if sw.get("class_type") == "ComfySwitchNode":
                    on_true = (sw.get("inputs") or {}).get("on_true")
                    if isinstance(on_true, list):
                        l = graph.get(str(on_true[0])) or {}
                        through_lora = "Lora" in str(l.get("class_type", ""))
    rows.append({
        "pid": pid[:8], "secs": secs, "switch": switch, "steps": chosen,
        "lora": bool(lora), "through_lora": through_lora,
        "frames": frames, "size": f"{w}x{h}",
        "out": [i.get("filename") for v in (rec.get("outputs") or {}).values()
                if isinstance(v, dict) for i in (v.get("images") or [])],
    })

rows.sort(key=lambda r: r["secs"])
out.append(f"{'pid':9} {'耗时':>9} {'开关':>5} {'步数':>5} {'LoRA在路径':>9} "
           f"{'帧':>5} {'分辨率':>10}  输出")
for r in rows:
    out.append(f"{r['pid']:9} {r['secs']/60:7.1f}分 {str(r['switch']):>5} "
               f"{str(r['steps']):>5} {str(r['through_lora']):>9} "
               f"{str(r['frames']):>5} {r['size']:>10}  {r['out'][:1]}")

# --- the two groups ----------------------------------------------------
out.append("")
out.append("=== 按开关分组 ===")
for sw in (True, False, None):
    g = [r for r in rows if r["switch"] == sw]
    if not g:
        continue
    avg = sum(r["secs"] for r in g) / len(g)
    fps = [r["frames"] for r in g if isinstance(r["frames"], (int, float))]
    out.append(f"  开关={sw}: {len(g)} 次，平均 {avg/60:.1f} 分钟"
               + (f"，帧数 {fps}" if fps else ""))

# --- what a fast one looked like --------------------------------------
out.append("")
out.append("=== 最快的一次（你手动跑的可能就是这种）===")
if rows:
    r = rows[0]
    out.append(f"  {json.dumps(r, ensure_ascii=False)}")
    # what that job's model path was
    rec = hist.get(r["pid"]) or next(
        (v for k, v in hist.items() if k.startswith(r["pid"])), None)
    if rec:
        p = rec.get("prompt")
        graph = p[2] if isinstance(p, list) and len(p) > 2 else {}
        for nid, node in graph.items():
            ct = str(node.get("class_type", ""))
            if ct in ("LoraLoaderModelOnly", "PrimitiveInt", "PrimitiveBoolean",
                      "ComfySwitchNode", "PathchSageAttentionKJ",
                      "BasicScheduler", "KSamplerSelect"):
                out.append(f"    #{nid} {ct}: "
                           f"{json.dumps(node.get('inputs'), ensure_ascii=False)[:150]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\speed.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
