"""Watch the renders and report how long each one takes.

The switch was off and the sampler doing twenty steps without the LoRA;
it is now on, with eight. Whether that is the three times faster the
numbers say it should be is only knowable from the cards' own timings, so
every job that finishes is timed and grouped by the settings it ran with
- and the first one on the new settings is called out, since that is the
measurement the change was made for.

Run in the background; writes its findings as it goes.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

CARD = "http://192.168.31.7:8188"
LOG = Path(r"C:\Users\David\AppData\Local\Temp\opencode\speed_watch.txt")
SEEN: set[str] = set()
DEADLINE = time.time() + 3 * 3600


def note(lines):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def settings_of(graph: dict):
    switch = None
    fast_steps = None
    lora_in_path = False
    for n in graph.values():
        ct = str(n.get("class_type", ""))
        ins = n.get("inputs") or {}
        if ct == "PrimitiveBoolean":
            switch = ins.get("value")
        if ct == "PathchSageAttentionKJ":
            m = ins.get("model")
            if isinstance(m, list):
                sw = graph.get(str(m[0])) or {}
                if sw.get("class_type") == "ComfySwitchNode":
                    on_true = (sw.get("inputs") or {}).get("on_true")
                    if isinstance(on_true, list):
                        l = graph.get(str(on_true[0])) or {}
                        lora_in_path = "Lora" in str(l.get("class_type", ""))
    # the step value the switch selects
    for n in graph.values():
        if str(n.get("class_type", "")) != "ComfySwitchNode":
            continue
        ins = n.get("inputs") or {}
        if not (ins.get("switch") and isinstance(ins.get("on_true"), list)):
            continue
        on_false = ins.get("on_false")
        if not isinstance(on_false, list):
            continue
        # is this the steps switch? its branch values are ints
        for src in (on_false, ins.get("on_true")):
            node = graph.get(str(src[0])) or {}
            if node.get("class_type") == "PrimitiveInt":
                chosen = ins.get("on_true") if switch else on_false
                cn = graph.get(str(chosen[0])) or {}
                fast_steps = (cn.get("inputs") or {}).get("value")
    frames = None
    for n in graph.values():
        if "ReferenceToVideo" in str(n.get("class_type", "")):
            v = (n.get("inputs") or {}).get("length")
            if isinstance(v, (int, float)):
                frames = v
    return switch, fast_steps, lora_in_path, frames


note([f"=== 开始监控 {time.strftime('%H:%M:%S')} ==="])

while time.time() < DEADLINE:
    try:
        with urllib.request.urlopen(CARD + "/history?max_items=40", timeout=30) as r:
            hist = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        note([f"{time.strftime('%H:%M:%S')} 读历史失败 {e}"])
        time.sleep(30)
        continue

    for pid, rec in hist.items():
        if pid in SEEN:
            continue
        msgs = (rec.get("status") or {}).get("messages") or []
        t0 = t1 = None
        for m in msgs:
            if isinstance(m, list) and len(m) >= 2:
                k, d = m[0], m[1] or {}
                if k == "execution_start":
                    t0 = d.get("timestamp")
                elif k in ("execution_success", "execution_error",
                           "execution_interrupted"):
                    t1 = d.get("timestamp")
        if not (t0 and t1):
            continue
        SEEN.add(pid)
        secs = (t1 - t0) / 1000.0
        p = rec.get("prompt")
        g = p[2] if isinstance(p, list) and len(p) > 2 and isinstance(p[2], dict) else {}
        sw, steps, lora, frames = settings_of(g) if g else (None, None, None, None)
        outs = [i.get("filename") for v in (rec.get("outputs") or {}).values()
                if isinstance(v, dict) for i in (v.get("images") or [])]
        status = (rec.get("status") or {}).get("status_str")
        fps = (secs / frames) if frames else 0
        note([f"{time.strftime('%H:%M:%S')} pid={pid[:8]} {secs/60:5.1f}分 "
              f"状态={status} 开关={sw} 步数={steps} LoRA在路径={lora} "
              f"帧={frames} 每帧={fps:.1f}s 输出={outs}"])
    time.sleep(20)

note([f"=== 监控结束 {time.strftime('%H:%M:%S')} ==="])
