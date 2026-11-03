"""The config after the swap: parses, loads, and points where it should.

A YAML file that does not parse takes the whole console down, and a
mapping that still names a node the new file does not have reports a
problem on every check while writing nothing at runtime - so both are
read back here rather than assumed from the edits.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

import yaml   # noqa: E402

out = []
p = Path(r"E:\dramakit\config\default.yaml")
try:
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    out.append("✓ YAML 解析通过")
except Exception as e:  # noqa: BLE001
    out.append(f"✗ YAML 解析失败: {e}")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\krea2cfg.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

c = d["comfyui"]
out.append("")
out.append("=== comfyui 关键项 ===")
for k in ("t2i_workflow", "t2i_workflow_ref", "i2v_workflow", "checkpoint",
          "prompt_format", "local_roles", "base_url"):
    out.append(f"  {k:18} = {c.get(k)!r}")
out.append("  t2i_nodes:")
for k, v in (c.get("t2i_nodes") or {}).items():
    out.append(f"      {k:12} = {v!r}")
out.append("  i2v_nodes:")
for k, v in (c.get("i2v_nodes") or {}).items():
    out.append(f"      {k:12} = {v!r}")

# --- through the real loader -------------------------------------------
from dramakit.config import Config   # noqa: E402
cfg = Config.load(Config.discover())
out.append("")
out.append("=== Config.load ===")
out.append(f"  t2i_workflow     = {cfg.comfyui.t2i_workflow}")
out.append(f"  t2i_workflow_ref = {cfg.comfyui.t2i_workflow_ref}")
out.append(f"  i2v_workflow     = {cfg.comfyui.i2v_workflow}")
out.append(f"  checkpoint       = {cfg.comfyui.checkpoint}")
out.append(f"  sampling         = {cfg.comfyui.t2i_nodes.get('sampling')!r}")
out.append(f"  ref_views        = {cfg.characters.ref_views}")
out.append(f"  ref_audio_node   = {cfg.comfyui.ref_audio_node}")

# --- the workflows exist, and hold what the mapping names ---------------
import json   # noqa: E402
out.append("")
out.append("=== 工作流文件 ===")
root = Path(r"E:\dramakit")
for rel in (cfg.comfyui.t2i_workflow, cfg.comfyui.t2i_workflow_ref,
            cfg.comfyui.i2v_workflow):
    f = root / rel
    if not f.exists():
        out.append(f"  ✗ {rel}  **文件不存在**")
        continue
    g = json.loads(f.read_text(encoding="utf-8"))
    out.append(f"  ✓ {rel}  {len(g)} 节点")
    if "krea2" in rel or "t2i" in rel:
        for sem, nid in (cfg.comfyui.t2i_nodes or {}).items():
            if not nid:
                out.append(f"      {sem:12} -> (空，不写)")
                continue
            ok = str(nid) in g
            out.append(f"      {sem:12} -> #{nid} "
                       f"{'✓' if ok else '**不存在**'}")

# --- and the files those workflows name --------------------------------
out.append("")
out.append("=== 工作流引用的模型文件 ===")
mroot = Path(r"E:\ComfyUI\models")
need = set()
for rel in (cfg.comfyui.t2i_workflow, cfg.comfyui.t2i_workflow_ref):
    f = root / rel
    if not f.exists():
        continue
    g = json.loads(f.read_text(encoding="utf-8"))
    for n in g.values():
        ins = n.get("inputs") or {}
        for k in ("unet_name", "clip_name", "vae_name", "lora_name"):
            if ins.get(k):
                need.add((k, ins[k]))
for k, name in sorted(need):
    sub = {"unet_name": "diffusion_models", "clip_name": "text_encoders",
           "vae_name": "vae", "lora_name": "loras"}[k]
    f = mroot / sub / name
    out.append(f"  {'✓' if f.exists() else '✗'} {sub}/{name}"
               + (f"  {f.stat().st_size/1024**3:.2f} GiB" if f.exists() else "  **缺失**"))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\krea2cfg.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
