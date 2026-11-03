"""Where the clip went, and why every still has the same seed.

One video was sent to the card six minutes ago and the queue is empty
again, with no clip on disk and no error in the log. Either it finished
and nothing took the result, or it was refused, and the card's own
history is the only record that says which.

Every still carries the same seed too. A still per shot is meant to
differ from the next, or every shot in the episode is the same picture
drawn from the same noise - and that is not something a log line shows,
because each line looks correct on its own.
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

CARD = "http://192.168.31.7:8188"
LOCAL = "http://127.0.0.1:8188"
out = []


def get(base, path, timeout=30):
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


# --- the card's history ------------------------------------------------
hist = get(CARD, "/history?max_items=6")
out.append("=== 3090 最近执行 ===")
if "error" in hist:
    out.append(f"  {hist['error']}")
for pid, rec in hist.items():
    p = rec.get("prompt")
    graph = p[2] if isinstance(p, list) and len(p) > 2 else {}
    st = (rec.get("status") or {}).get("status_str")
    outs = rec.get("outputs") or {}
    files = [i.get("filename") for v in outs.values()
             if isinstance(v, dict) for i in (v.get("images") or [])]
    n136 = graph.get("136", {}).get("inputs", {}) if isinstance(graph, dict) else {}
    out.append(f"  pid={pid[:8]} 节点={len(graph) if isinstance(graph, dict) else 0} "
               f"status={st} 输出={files}")
    if n136:
        out.append(f"      length={n136.get('length')} width={n136.get('width')} "
                   f"height={n136.get('height')}")
    # any error the card recorded
    msgs = (rec.get("status") or {}).get("messages") or []
    for m in msgs:
        if isinstance(m, list) and m and "error" in str(m[0]).lower():
            out.append(f"      **{json.dumps(m, ensure_ascii=False)[:300]}**")
    # the last message often carries the failure
    if msgs:
        out.append(f"      末条消息: {json.dumps(msgs[-1], ensure_ascii=False)[:300]}")

q = get(CARD, "/queue")
out.append("")
out.append("=== 3090 当前队列 ===")
out.append(f"  运行 {len(q.get('queue_running') or [])} | "
           f"等待 {len(q.get('queue_pending') or [])}")

# --- the stills on disk, and their seeds ------------------------------
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
out.append("")
out.append("=== 出图记录里的种子 ===")
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
seeds: dict[str, int] = {}
shown = 0
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            gm = sh.get("gen_meta") or {}
            s = gm.get("seed")
            if s is not None:
                seeds[str(s)] = seeds.get(str(s), 0) + 1
                if shown < 6:
                    out.append(f"  {sh.get('id')}  seed={s}  "
                               f"image={sh.get('image_path')}  video={sh.get('video_path')}")
                    shown += 1
out.append("")
out.append(f"  出现过的不同种子数: {len(seeds)}")
for s, n in sorted(seeds.items(), key=lambda x: -x[1])[:6]:
    out.append(f"      seed={s}  用了 {n} 次")

# --- what _seed_for does ----------------------------------------------
out.append("")
out.append("=== _seed_for 的实现 ===")
import inspect   # noqa: E402
from dramakit.pipeline import visual as V   # noqa: E402
out.append(inspect.getsource(V._seed_for))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\videogone.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
