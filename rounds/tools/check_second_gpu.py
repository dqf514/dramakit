"""Does the second card work, before the console is restarted?

The console builds its pool when a run starts, so the card that has
just been added is not in the running one.  This builds the pool the
way the console would - from the config as it now is - and asks it the
questions: is the card there, does it answer, does it have the
weights the video workflow needs, and how many videos can run at once.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config  # noqa: E402
from dramakit.providers.pool import build_pool  # noqa: E402

cfg = Config.load(Config.discover())
pool = build_pool(cfg, pathlib.Path("."))
print("  出视频并发:", cfg.comfyui.video_concurrency)
print("  节点池里的卡:")
for n in pool.nodes:
    roles = ",".join(sorted(n.roles)) or "（什么都接）"
    try:
        alive = n.client.ping()
    except Exception as e:  # noqa: BLE001
        alive = "**%s**" % str(e)[:50]
    print("     %-12s %-26s %-10s 在=%-5s 深度=%s 最多同时 %s 个"
          % (n.name, n.spec.base_url, roles, alive, n.depth(), n.max_concurrent))

i2v = [n for n in pool.nodes if n.takes("i2v")]
ok = [n for n in i2v if n.client.ping()]
print("  能出视频的卡: %d 张 -> %s" % (len(ok), [n.name for n in ok]))
print("  同时能跑几段视频:", max(1, len(ok)))

# and the weights: the video workflow names them, the card has to have them
try:
    from dramakit.providers.nodes import manifest
    refs = manifest(cfg, pathlib.Path("."))
except Exception as e:  # noqa: BLE001
    refs = []
    print("  清单读不出来:", str(e)[:120])
if refs:
    from dramakit.providers.nodes import check_node
    for n in i2v:
        try:
            health = check_node(n.spec, refs)
        except Exception as e:  # noqa: BLE001
            print("     %s 查不到模型: %s" % (n.name, str(e)[:80]))
            continue
        missing = list(getattr(health, "missing", []) or [])
        print("     %-12s 缺 %d 个: %s" % (n.name, len(missing), missing[:4]))
