"""What differs between the fast clips and the slow ones, node by node.

Two things could make a clip cost three times another at the same size
and length: the sampler doing more work, or the attention patch doing
less. Both are readable off the jobs themselves - the scheduler's step
count, the attention mode, how many pictures went in as references - so
the two graphs are laid side by side rather than reasoned about.
"""
import json
import sys
import urllib.request
from pathlib import Path

CARD = "http://192.168.31.7:8188"
out = []

with urllib.request.urlopen(CARD + "/history?max_items=60", timeout=40) as r:
    hist = json.loads(r.read())


def dur(rec):
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
    return (t1 - t0) / 1000.0 if (t0 and t1) else 0.0


def graph_of(rec):
    p = rec.get("prompt")
    return p[2] if isinstance(p, list) and len(p) > 2 and isinstance(p[2], dict) else {}


def describe(pid: str, rec: dict) -> None:
    g = graph_of(rec)
    out.append(f"--- {pid[:8]}  {dur(rec)/60:.1f} 分钟  {len(g)} 节点 ---")
    want = ("BasicScheduler", "KSamplerSelect", "PathchSageAttentionKJ",
            "LoraLoaderModelOnly", "UNETLoader", "CLIPLoader", "VAELoader",
            "MiniMaxH3ReferenceToVideo", "PrimitiveBoolean", "PrimitiveInt",
            "ComfySwitchNode", "RandomNoise", "ResolutionSelector",
            "BasicGuider", "SamplerCustomAdvanced")
    for nid, n in sorted(g.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        ct = str(n.get("class_type", ""))
        if ct not in want:
            continue
        ins = n.get("inputs") or {}
        # show only what decides cost, not every wire
        keep = {k: v for k, v in ins.items()
                if k in ("steps", "scheduler", "sampler_name", "denoise",
                         "sage_attention", "allow_compile", "lora_name",
                         "strength_model", "unet_name", "clip_name", "vae_name",
                         "value", "switch", "on_false", "on_true", "prompt",
                         "noise_seed", "aspect_ratio", "megapixels",
                         "width", "height", "length", "model", "cfg",
                         "control_after_generate")}
        # a long prompt is not a setting
        if isinstance(keep.get("prompt"), str):
            keep["prompt"] = f"<{len(keep['prompt'])} 字符>"
        if isinstance(keep.get("length"), list):
            src = g.get(str(keep["length"][0])) or {}
            keep["length"] = f"来自#{keep['length'][0]} " + json.dumps(
                (src.get("inputs") or {}), ensure_ascii=False)[:80]
        out.append(f"  #{nid:<5} {ct:<30} {json.dumps(keep, ensure_ascii=False)[:230]}")
    # how many references actually went in
    for nid, n in g.items():
        if "ReferenceToVideo" in str(n.get("class_type", "")):
            ins = n.get("inputs") or {}
            imgs = [k for k in ins if k.startswith("ref_images.")]
            auds = [k for k in ins if k.startswith("ref_audios.")]
            out.append(f"      参考图 {len(imgs)} 个: {imgs}")
            out.append(f"      参考音频 {len(auds)} 个: {auds}")
    out.append("")


# --- one fast, one slow, both from the new workflow --------------------
rows = []
for pid, rec in hist.items():
    g = graph_of(rec)
    if not g or dur(rec) <= 0:
        continue
    n = len(g)
    has_new = any("ReferenceToVideo" in str(x.get("class_type", ""))
                  for x in g.values())
    rows.append((dur(rec), pid, rec, n, has_new))

rows.sort()
new_rows = [r for r in rows if r[4]]
if new_rows:
    describe(*new_rows[0][1:3])       # fastest new
    describe(*new_rows[-1][1:3])      # slowest new
old_rows = [r for r in rows if not r[4]]
if old_rows:
    describe(*old_rows[-1][1:3])      # slowest old

# --- the two workflow files, sampling side by side ---------------------
out.append("")
out.append("=== 两个工作流文件的采样设置 ===")
for label, rel in (("旧 i2v_minimax_h3_ref2v_audio",
                    r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v_audio.json"),
                   ("新 i2v_shortdrama",
                    r"E:\dramakit\config\comfyui\i2v_shortdrama.json")):
    p = Path(rel)
    if not p.exists():
        out.append(f"  {label}: 文件不存在")
        continue
    g = json.loads(p.read_text(encoding="utf-8"))
    out.append(f"  {label} ({len(g)} 节点):")
    for nid, n in g.items():
        ct = str(n.get("class_type", ""))
        ins = n.get("inputs") or {}
        if ct in ("BasicScheduler", "KSamplerSelect", "PathchSageAttentionKJ",
                  "PrimitiveBoolean", "PrimitiveInt", "LoraLoaderModelOnly"):
            keep = {k: v for k, v in ins.items()
                    if k in ("steps", "scheduler", "sampler_name", "denoise",
                             "sage_attention", "allow_compile", "lora_name",
                             "strength_model", "value", "switch", "on_false",
                             "on_true", "model")}
            out.append(f"    #{nid:<5} {ct:<28} {json.dumps(keep, ensure_ascii=False)[:200]}")
    # is the attention patch even present?
    sage = [nid for nid, n in g.items()
            if "SageAttention" in str(n.get("class_type", ""))]
    out.append(f"    SageAttention 节点: {sage or '无'}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\diff.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
