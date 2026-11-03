"""The exact blocks in the config that have to change, verbatim.

Replaced by structure rather than by eye: the file carries comments in
Chinese and the shell mangles them, so the anchors are taken from the file
itself rather than retyped.
"""
from pathlib import Path

cfg = Path(r"E:\dramakit\config\default.yaml")
lines = cfg.read_text(encoding="utf-8").split("\n")
out = []

for i, line in enumerate(lines):
    if line.strip().startswith("i2v_workflow:"):
        out.append(f"--- i2v_workflow @ {i+1} ---")
        out.append(repr(line))
    if line.strip().startswith("i2v_nodes:"):
        out.append(f"--- i2v_nodes @ {i+1} ---")
        for j in range(i, min(i + 14, len(lines))):
            out.append(f"  {j+1}: {lines[j]!r}")
    if line.strip() == "graph_overrides:":
        out.append(f"--- graph_overrides @ {i+1} ---")
        for j in range(i, min(i + 5, len(lines))):
            out.append(f"  {j+1}: {lines[j]!r}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\yamlblocks.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
