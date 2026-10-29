"""Let the local machine keep one role.

The 5080 makes the stills fast, and the 3090s have the cards free for the
video. If the local machine takes video jobs too, the two kinds of work
fight over its memory and the stills slow down.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    nodes: list[NodeConfig] = Field(default_factory=list)"""
new = """    nodes: list[NodeConfig] = Field(default_factory=list)
    # What the local machine is for: [] = anything, ["t2i"] = only the stills
    local_roles: list[str] = Field(default_factory=list)"""
assert old in s, "config 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py 已改（本机角色）")

p = Path(r"E:\\dramakit\\dramakit\\providers\\pool.py")
s = p.read_text(encoding="utf-8")
old = """    local_cfg = base.model_copy()
    nodes.append(_Node(local, local_cfg, root))"""
new = """    local_cfg = base.model_copy()
    local.roles = list(getattr(base, "local_roles", None) or [])
    nodes.append(_Node(local, local_cfg, root))"""
assert old in s, "pool 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("pool.py 已改")

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = "  nodes:\n    - name: gpu3090-a"
new = "  local_roles: [t2i]                      # 本机只出图，视频交给 3090\n  nodes:\n    - name: gpu3090-a"
assert old in s, "yaml 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml 已改")
