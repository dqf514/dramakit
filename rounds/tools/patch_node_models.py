"""Let every node use its own weights.

The same pipeline runs on machines with different cards, and the weights
are built for the card they sit on: the 5080 takes the nvfp4 files, the
3090 (Ampere, no fp4 tensor cores) takes the int8/convrot ones. The
workflow names the files, so a node needs to be able to say "use this
file instead" for the loader nodes.
"""
from pathlib import Path

# 1) the config: per node overrides of the workflow's loader fields
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    extra_headers: dict = Field(default_factory=dict)
    verify_tls: bool = True"""
new = """    extra_headers: dict = Field(default_factory=dict)
    verify_tls: bool = True
    # This node's own weights: {"6": {"unet_name": "..."}} - the loader
    # nodes of the workflow. The 5080 takes the nvfp4 files, the 3090 the
    # int8/convrot ones.
    graph_overrides: dict = Field(default_factory=dict)"""
assert old in s, "config 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py 已改（节点级权重覆盖）")

# 2) the client: apply them to the graph it loads
p = Path(r"E:\\dramakit\\dramakit\\providers\\comfyui.py")
s = p.read_text(encoding="utf-8")
old = """        self.cfg = cfg
        self.base = cfg.base_url.rstrip("/")"""
new = """        self.cfg = cfg
        self.base = cfg.base_url.rstrip("/")
        # this node's own weights (the loader nodes of the workflow)
        self.graph_overrides: dict = getattr(cfg, "graph_overrides", None) or {}"""
if old in s:
    s = s.replace(old, new, 1)
else:
    # find the constructor body
    i = s.index("class ComfyUIClient")
    j = s.index("self.base = cfg.base_url.rstrip(\"/\")", i)
    k = j + len("self.base = cfg.base_url.rstrip(\"/\")")
    s = (s[:k] + "\n        # this node's own weights (the loader nodes of the workflow)"
         + "\n        self.graph_overrides: dict = "
           "getattr(cfg, \"graph_overrides\", None) or {}" + s[k:])

old = """        for nid, fields in (extra.get("graph_overrides") or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)

        pid = self._queue(graph)
        log.info("ComfyUI i2v 已提交 pid=%s seed=%s @ %s", pid, real_seed, self.base)"""
new = """        for nid, fields in (extra.get("graph_overrides") or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)
        # this node's own weights
        for nid, fields in (self.graph_overrides or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)

        pid = self._queue(graph)
        log.info("ComfyUI i2v 已提交 pid=%s seed=%s @ %s", pid, real_seed, self.base)"""
assert old in s, "i2v 锚点没找到"
s = s.replace(old, new, 1)

old = """        for nid, fields in (extra.get("graph_overrides") or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)

        pid = self._queue(graph)
        log.info("ComfyUI t2i 已提交 pid=%s seed=%s @ %s", pid, real_seed, self.base)"""
new = """        for nid, fields in (extra.get("graph_overrides") or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)
        for nid, fields in (self.graph_overrides or {}).items():
            if nid in graph:
                graph[nid].setdefault("inputs", {}).update(fields)

        pid = self._queue(graph)
        log.info("ComfyUI t2i 已提交 pid=%s seed=%s @ %s", pid, real_seed, self.base)"""
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("comfyui.py 已改（节点级权重覆盖）")

# 3) the pool: hand the overrides to the node's client
p = Path(r"E:\\dramakit\\dramakit\\providers\\pool.py")
s = p.read_text(encoding="utf-8")
old = """        node_cfg.extra_headers = spec.extra_headers or {}
        node_cfg.verify_tls = spec.verify_tls
        nodes.append(_Node(spec, node_cfg, root))"""
new = """        node_cfg.extra_headers = spec.extra_headers or {}
        node_cfg.verify_tls = spec.verify_tls
        node_cfg.graph_overrides = dict(spec.graph_overrides or {})
        nodes.append(_Node(spec, node_cfg, root))"""
assert old in s, "pool 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("pool.py 已改")
