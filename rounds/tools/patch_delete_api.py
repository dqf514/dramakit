"""Delete a project.

The console could make projects and could not delete them, so the test
ones piled up next to the work.  A project is a folder; deleting one
means moving it out of the way first - a project that took an hour of
rendering should not disappear with a mis-click.
"""
from pathlib import Path
import shutil

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

if '"/api/projects/delete"' not in s:
    old = """            if path == "/api/reindex":
                return self._json(self._api_reindex(body))"""
    new = """            if path == "/api/reindex":
                return self._json(self._api_reindex(body))
            if path == "/api/projects/delete":
                return self._json(self._api_projects_delete(body))"""
    assert old in s, "路由锚点没找到"
    s = s.replace(old, new, 1)

    old2 = """        def _api_catalog(self, body: dict) -> dict:"""
    new2 = '''        def _api_projects_delete(self, body: dict) -> dict:
            """A project, out of the way.

            It goes to projects/_trash first: a project that took hours of
            rendering should not vanish on a mis-click, and the trash is
            there to be emptied by hand when the user is sure.
            """
            slug = (body.get("project") or "").strip()
            if not slug:
                return {"ok": False, "error": "project required"}
            store = state.open_store(slug)
            if not store:
                return {"ok": False, "error": "项目不存在"}
            root = store.root.resolve()
            base = state.projects_root.resolve()
            if root.parent != base:
                return {"ok": False, "error": "项目不在项目目录里"}
            trash = base / "_trash"
            trash.mkdir(exist_ok=True)
            dest = trash / root.name
            if dest.exists():
                dest = trash / f"{root.name}_{int(time.time())}"
            shutil.move(str(root), str(dest))
            try:
                state.catalog.reindex_project(ProjectStore(base), with_ai=False)
            except Exception:  # noqa: BLE001
                pass
            return {"ok": True, "project": slug, "moved_to": str(dest)}

        def _api_catalog(self, body: dict) -> dict:'''
    assert old2 in s, "处理器锚点没找到"
    s = s.replace(old2, new2, 1)

    # time is used by the name it falls back to
    if "\nimport time" not in s:
        s = s.replace("\nimport shutil\n", "\nimport shutil\nimport time\n", 1)

p.write_text(s, encoding="utf-8")
print("web/server.py: /api/projects/delete（先移到 _trash，不直接删）")
