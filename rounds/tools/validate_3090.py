"""Validate the new workflow against the card it will actually run on.

The self-check prints against the configured base url, which is the 5080 -
but this workflow is for the 3090, and a node type missing there is the
difference between a render and an error at submit time. Markdown notes and
the attention patch are the ones to look at: a note is a comment that the
card does not have to know about, while a patch sitting in the model chain
is a wire that has to exist.

It also reports what the pipeline would write, so a mapping that lands on
the wrong node shows up here rather than as a render of the placeholder.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.providers.comfyui import ComfyUIClient  # noqa: E402

HOST = "http://192.168.31.7:8188"
cfg = Config.load(Config.discover())

out = []
# point the client at the card the workflow belongs to
cfg.comfyui.base_url = HOST
c = ComfyUIClient(cfg.comfyui, root=Path(r"E:\dramakit"))

rep = c.validate_workflow(cfg.comfyui.i2v_workflow, cfg.comfyui.i2v_nodes, "i2v")
out.append(f"=== {cfg.comfyui.i2v_workflow} 对 {HOST} ===")
out.append(f"  节点数 {rep.get('nodes')}  kind={rep.get('kind')}  ok={rep['ok']}")
for p in rep.get("problems") or []:
    out.append("  [问题] " + p)
for w in rep.get("warnings") or []:
    out.append("  [提醒] " + w)
out.append("  自动识别: " + " · ".join(
    f"{k}={v}" for k, v in (rep.get("inferred") or {}).items()))

# ---- which nodes the card does not have, and what they are wired to -----
graph = c._load_workflow(cfg.comfyui.i2v_workflow, "i2v")
have = c.available_node_types()
missing = {nid: n.get("class_type") for nid, n in graph.items()
           if n.get("class_type") and n.get("class_type") not in have}

out.append("")
out.append("=== 卡上没有的节点类型 ===")
if not missing:
    out.append("  （无）")
for nid, ct in missing.items():
    node = graph[nid]
    ins = node.get("inputs", {})
    wires = {k: v for k, v in ins.items() if isinstance(v, list)}
    out.append(f"  #{nid} {ct}")
    out.append(f"      接线: {json.dumps(wires, ensure_ascii=False)}")
    out.append(f"      值  : {json.dumps({k: v for k, v in ins.items() if not isinstance(v, list)}, ensure_ascii=False)[:160]}")
    # who feeds it, and who it feeds
    fed_by = [f"#{a}({b})" for a, n in graph.items()
              for v in (n.get("inputs") or {}).values()
              if isinstance(v, list) and str(v[0]) == nid]
    feeds = [f"#{a}({b})" for a, n in graph.items()
             for v in (n.get("inputs") or {}).values()
             if isinstance(v, list) and str(v[0]) == nid]
    out.append(f"      谁喂它: {', '.join(fed_by) or '（无，是源头）'}")

# ---- the chain from model loader to sampler ----------------------------
out.append("")
out.append("=== 模型链路（UNET → LoRA → 谁在中间）===")
for nid, node in graph.items():
    ct = node.get("class_type", "")
    if ct in ("UNETLoader", "LoraLoaderModelOnly", "BasicGuider",
              "SamplerCustomAdvanced", "PathchSageAttentionKJ",
              "MiniMaxH3ReferenceToVideo", "KSamplerSelect",
              "BasicScheduler", "RandomNoise"):
        ins = node.get("inputs", {})
        wires = {k: v for k, v in ins.items() if isinstance(v, list)}
        out.append(f"  #{nid:<5} {ct:<32} {json.dumps(wires, ensure_ascii=False)[:150]}")

# ---- what the pipeline would write ------------------------------------
out.append("")
out.append("=== 管线会写入的值 ===")
nm = cfg.comfyui.i2v_nodes
for sem, field in (("positive", "prompt"), ("positive", "text"),
                   ("frames", "length"), ("width", "width"),
                   ("height", "height"), ("seed", "noise_seed"),
                   ("fps", "fps"), ("image", "image")):
    nid = str(nm.get(sem) or "")
    node = graph.get(nid)
    if not node:
        out.append(f"  {sem:8} -> #{nid}  不存在")
        continue
    has = field in (node.get("inputs") or {})
    cur = (node.get("inputs") or {}).get(field)
    shown = cur if not isinstance(cur, list) else f"来自 #{cur[0]}"
    out.append(f"  {sem:8} -> #{nid} {node.get('class_type'):<30} "
               f"字段 {field}: {'有' if has else '**没有**'} 当前={shown!r}")

# ---- the nodes the config names exist? --------------------------------
out.append("")
out.append("=== 配置的每个语义 id 是否在图里 ===")
for sem, nid in nm.items():
    ok = str(nid) in graph if nid else True
    mark = "✓" if ok else "✗ 不存在"
    out.append(f"  {sem:10} -> {str(nid):6} {mark}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\v3090.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
