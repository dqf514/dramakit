"""Point the local card at Krea-2, and drop the node the model does not have.

The pipeline writes to a workflow by node id and picks a second file when
a shot brings reference pictures, so both files change together - one
would leave the first frames rendered by a model whose text encoder the
other does not use.

The flux shift node goes from the mapping as well. Krea-2 does not take
one, and a mapping that names a node the file no longer holds reports a
problem on every check while writing nothing at runtime: the value would
be aimed at a node that is not there.
"""
import re
from pathlib import Path

p = Path(r"E:\dramakit\config\default.yaml")
lines = p.read_text(encoding="utf-8").split("\n")
out = []

# --- the workflows and the weights -------------------------------------
subs = {
    "t2i_workflow:": "t2i_workflow: config/comfyui/t2i_krea2.json",
    "t2i_workflow_ref:": "t2i_workflow_ref: config/comfyui/t2i_krea2_ref.json",
    "checkpoint:": '    checkpoint: krea2_turbo_nvfp4.safetensors',
}
done = set()
for i, line in enumerate(lines):
    s = line.strip()
    for key, repl in subs.items():
        if s.startswith(key) and key not in done:
            indent = line[: len(line) - len(line.lstrip())]
            # keep any trailing comment
            comment = ""
            m = re.search(r"\s{2,}#.*$", line)
            if m:
                comment = "   " + m.group(0).strip()
            lines[i] = indent + repl + comment
            done.add(key)
            out.append(f"  {key} -> {repl}")

# --- the mapping: Krea-2 has no flux shift node -------------------------
for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith("sampling:") and "t2i_nodes" in "\n".join(lines[max(0, i - 15):i]):
        indent = line[: len(line) - len(line.lstrip())]
        lines[i] = f'{indent}sampling: ""   # Krea-2 无 ModelSamplingFlux，留空=不写'
        out.append("  t2i_nodes.sampling -> 空")
        break

p.write_text("\n".join(lines), encoding="utf-8")

# --- verify -------------------------------------------------------------
import yaml   # noqa: E402
d = yaml.safe_load(p.read_text(encoding="utf-8"))
c = d["comfyui"]
out.append("")
out.append("=== 改后 ===")
out.append(f"  t2i_workflow     = {c.get('t2i_workflow')}")
out.append(f"  t2i_workflow_ref = {c.get('t2i_workflow_ref')}")
out.append(f"  checkpoint       = {c.get('checkpoint')}")
out.append(f"  sampling         = {(c.get('t2i_nodes') or {}).get('sampling')!r}")
out.append(f"  i2v_workflow     = {c.get('i2v_workflow')}  (未动)")
out.append(f"  local_roles      = {c.get('local_roles')}")

# and the config still loads through the real loader
import sys   # noqa: E402
sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config   # noqa: E402
cfg = Config.load(Config.discover())
out.append("")
out.append("=== Config.load ===")
out.append(f"  t2i_workflow     = {cfg.comfyui.t2i_workflow}")
out.append(f"  checkpoint       = {cfg.comfyui.checkpoint}")
out.append(f"  sampling         = {cfg.comfyui.t2i_nodes.get('sampling')!r}")
out.append(f"  ref_views        = {cfg.characters.ref_views}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\krea2cfg.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
