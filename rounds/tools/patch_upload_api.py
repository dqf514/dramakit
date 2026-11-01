"""Upload a novel, and the table of contents over the wire.

The console could take a path, which is a fine thing for a machine that
shares a disk with the pipeline and a poor thing for a browser.  So the
browser can send the file: it lands in the project's source folder, and
the book is cut into volumes and chapters before anything is written -
a million characters is not something to hand a model in one piece.
"""
from pathlib import Path
import re

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

# --------------------------------------------------------------------------- #
# 1. the upload endpoint
# --------------------------------------------------------------------------- #
if '"/api/upload"' not in s:
    old = """            if path == "/api/new":
                return self._json(self._api_new(body))"""
    new = """            if path == "/api/upload":
                return self._json(self._api_upload(body))
            if path == "/api/new":
                return self._json(self._api_new(body))
            if path == "/api/catalog":
                return self._json(self._api_catalog(body))"""
    assert old in s, "路由锚点没找到"
    s = s.replace(old, new, 1)

# the handlers
old2 = """        def _api_new(self, body: dict) -> dict:"""
new2 = '''        def _api_upload(self, body: dict) -> dict:
            """The browser's file, into the project's source folder.

            The body carries the name and the text: a browser cannot write
            to the machine's disk, and the pipeline reads from the disk.
            """
            name = (body.get("name") or "").strip()
            text = body.get("text") or ""
            slug = (body.get("project") or "").strip()
            if not text:
                return {"ok": False, "error": "文件是空的"}
            if slug:
                store = state.open_store(slug)
                if not store:
                    return {"ok": False, "error": "项目不存在"}
            else:
                name = name or "新项目"
                store = ProjectStore.create(state.projects_root, name)
            src_dir = store.root / "source"
            src_dir.mkdir(parents=True, exist_ok=True)
            fname = Path(name or "novel.txt").name
            if not fname.lower().endswith((".txt", ".md")):
                fname += ".txt"
            f = src_dir / fname
            f.write_text(text, encoding="utf-8")
            store.load()
            proj = store.load()
            proj.meta.source_file = str(f)
            store.save(proj)
            # and cut the book straight away, so the console can show the
            # table of contents and the user can pick the chapters
            info = {}
            try:
                from ..pipeline.catalog import run as catalog_run
                from ..pipeline.base import Context
                cfg = self.cfg if hasattr(self, "cfg") else None
                info = {"catalog": catalog_run(Context(cfg, store), str(f))}
            except Exception as e:  # noqa: BLE001
                info = {"catalog_error": str(e)[:300]}
            return {"ok": True, "project": store.root.name,
                    "path": str(f), "chars": len(text), **info}

        def _api_catalog(self, body: dict) -> dict:
            """The table of contents of a project, and its chosen chapters."""
            store = state.open_store(body.get("project", ""))
            if not store:
                return {"ok": False, "error": "项目不存在"}
            proj = store.load()
            return {"ok": True,
                    "volumes": proj.meta.volumes,
                    "chapters": [c.model_dump() for c in proj.meta.chapters],
                    "chosen": proj.meta.chosen_chapters,
                    "episodes_wanted": proj.meta.episodes_wanted}

        def _api_new(self, body: dict) -> dict:'''
assert old2 in s, "处理器锚点没找到"
s = s.replace(old2, new2, 1)

p.write_text(s, encoding="utf-8")
print("web/server.py: /api/upload + /api/catalog")
