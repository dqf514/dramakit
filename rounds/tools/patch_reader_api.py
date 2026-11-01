"""A chapter reader: click a chapter in the workbench and read the prose.

The catalogue already knows where each chapter's .txt lives, but nothing
would show it - a number and a title are not a story.  So a small endpoint
hands back the file's text, and a click on a chapter row or tile opens it
in a reader overlay that sits over the page.

The path is never taken from the request: the chapter index comes in, the
server looks the file up in the project's own catalogue, and the resolved
path is confirmed to sit inside the project.  A reader that would open any
file on disk is a reader that will eventually be asked to.
"""
import re
from pathlib import Path

srv = Path(r"E:\dramakit\dramakit\web\server.py")
s = srv.read_text(encoding="utf-8")

if "_api_chapter_read" in s:
    print("server.py: 阅读器接口已存在，跳过")
    raise SystemExit(0)

# 1) the route
anchor = '            if path == "/api/catalog":\n'
route = '            if path == "/api/chapter/read":\n                return self._json(self._api_chapter_read(body))\n'
assert anchor in s, "找不到 /api/catalog 路由锚点"
s = s.replace(anchor, route + anchor, 1)

# 2) the handler, as a method of the handler class (indented one level)
handler = '''
        def _api_chapter_read(self, body: dict) -> dict:
            """The text of one chapter, by its index in the project's catalogue."""
            store = state.open_store(body.get("project", ""))
            if not store:
                return {"ok": False, "error": "项目不存在"}
            try:
                idx = int(body.get("chapter", -1))
            except (TypeError, ValueError):
                return {"ok": False, "error": "chapter must be a number"}

            proj = store.load()
            ch = next((c for c in proj.meta.chapters if c.index == idx), None)
            if not ch:
                return {"ok": False, "error": f"第 {idx} 章不在目录里"}

            rel = (ch.file or "").replace("\\\\", "/").lstrip("/")
            if not rel:
                return {"ok": False, "error": "这一章没有文件"}

            root = store.root.resolve()
            fpath = (root / rel).resolve()
            # the file must live inside the project - never read outside it
            if not str(fpath).startswith(str(root)) or not fpath.is_file():
                return {"ok": False, "error": f"章节文件缺失：{rel}"}

            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception as e:  # noqa: BLE001
                log.error("chapter read failed: %s", traceback.format_exc())
                return {"ok": False, "error": f"读取失败：{e}"}

            return {"ok": True, "index": ch.index, "title": ch.title,
                    "volume": ch.volume, "chars": len(text), "text": text}

'''
# insert the handler right before the /api/catalog handler definition
hanchor = "        def _api_catalog(self, body: dict) -> dict:"
assert hanchor in s, "找不到 _api_catalog 定义锚点"
s = s.replace(hanchor, handler.lstrip("\n") + hanchor, 1)

srv.write_text(s, encoding="utf-8")
print("server.py: 加了 POST /api/chapter/read")
