import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config, NodeConfig
from dramakit.providers.pool import build_pool

cfg = Config.load(r"E:\dramakit\config\default.yaml")
cfg.comfyui.nodes = [
    NodeConfig(name="gpu3090-v0", base_url="http://127.0.0.1:8189",
               roles=["i2v"], transfer="scp"),
    NodeConfig(name="gpu3090-v1", base_url="http://127.0.0.1:8190",
               roles=["i2v"], transfer="scp"),
    NodeConfig(name="img-box", base_url="http://127.0.0.1:8191",
               roles=["t2i"], transfer="shared"),
]
p = build_pool(cfg, Path("E:/dramakit"))
print("节点:", [(n.name, sorted(n.roles)) for n in p.nodes])
print("t2i 候选:", [n.name for n in p.candidates("t2i")])
print("i2v 候选:", [n.name for n in p.candidates("i2v")])
print("ping:", p.ping())
print("health:", [(h["name"], h["online"], h["depth"]) for h in p.health()])
