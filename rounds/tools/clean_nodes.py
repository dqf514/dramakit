"""Take the leftover test card out of the node pool.

A card that was added by a test is still in the config, and the pool
asks every card whether it is answering - a card at a dead address
makes the pool slower for nothing.
"""
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.ai import autoconfig  # noqa: E402
from dramakit.config import Config  # noqa: E402

cfg = Config.load(Config.discover())
path = pathlib.Path(r"E:\dramakit\config\default.yaml")
nodes = list(cfg.comfyui.nodes or [])
keep = [n for n in nodes if not n.name.startswith("probe-")]
if len(keep) == len(nodes):
    print("  没有要清的")
else:
    for n in nodes:
        if n.name not in {k.name for k in keep}:
            print("  清掉 %s（%s）" % (n.name, n.base_url))
    autoconfig.save_nodes(path, [], {}, {}, remove=[n.name for n in nodes
                                                    if n.name not in {k.name for k in keep}])
    cfg2 = Config.load(path)
    print("  现在的节点：%s" % [n.name for n in (cfg2.comfyui.nodes or [])])
