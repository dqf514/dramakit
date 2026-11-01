"""The handler closes over the state; it can read the config from there."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

old = """                from ..pipeline.catalog import run as catalog_run
                from ..pipeline.base import Context
                cfg = getattr(self, "app", None) and getattr(self.app, "cfg", None)
                if cfg is None:
                    cfg = getattr(self, "cfg", None)
                info = {"catalog": catalog_run(Context(cfg, store), str(f))}"""
new = """                from ..pipeline.catalog import run as catalog_run
                from ..pipeline.base import Context
                cfg = state.cfg
                info = {"catalog": catalog_run(Context(cfg, store), str(f))}"""
assert old in s, "配置获取锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("web/server.py: 用 state.cfg")
