"""Pick the chapters, say how many episodes, and cut the book that way.

The user picks the chapters the drama is made from and says how many
episodes they want; the chapters are then cut into episodes, each episode
carrying the chapters it needs and nothing else.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

if '"/api/chapters/choose"' not in s:
    old = """            if path == "/api/catalog":
                return self._json(self._api_catalog(body))"""
    new = """            if path == "/api/catalog":
                return self._json(self._api_catalog(body))
            if path == "/api/chapters/choose":
                return self._json(self._api_chapters_choose(body))"""
    assert old in s, "路由锚点没找到"
    s = s.replace(old, new, 1)

    old2 = """        def _api_catalog(self, body: dict) -> dict:"""
    new2 = '''        def _api_chapters_choose(self, body: dict) -> dict:
            """The chapters the drama is made from, and how many episodes."""
            store = state.open_store(body.get("project", ""))
            if not store:
                return {"ok": False, "error": "项目不存在"}
            proj = store.load()
            chosen = body.get("chosen")
            if chosen is not None:
                proj.meta.chosen_chapters = [int(x) for x in chosen]
            want = body.get("episodes_wanted")
            if want:
                proj.meta.episodes_wanted = int(want)
            store.save(proj)
            return {"ok": True, "chosen": proj.meta.chosen_chapters,
                    "episodes_wanted": proj.meta.episodes_wanted}

        def _api_catalog(self, body: dict) -> dict:'''
    assert old2 in s, "处理器锚点没找到"
    s = s.replace(old2, new2, 1)

p.write_text(s, encoding="utf-8")
print("web/server.py: /api/chapters/choose")

# --------------------------------------------------------------------------- #
# segment: cut the chosen chapters into episodes, not the whole text
# --------------------------------------------------------------------------- #
q = Path(r"E:\\dramakit\\dramakit\\pipeline\\segment.py")
t = q.read_text(encoding="utf-8")
if "chosen_chapters" in t:
    print("segment.py: 已经改过了")
else:
    old3 = """    text = ctx.store.cleaned_text_path().read_text(encoding="utf-8")"""
    new3 = """    # the chapters the user picked, cut into episodes; the whole book is
    # only what the pick says it is
    chosen = list(ctx.project.meta.chosen_chapters or [])
    chapters_meta = ctx.project.meta.chapters or []
    if chosen and chapters_meta:
        blocks = []
        for c in chapters_meta:
            if c.index not in chosen:
                continue
            f = ctx.store.root / c.file if c.file else None
            if f and f.exists():
                blocks.append(f.read_text(encoding="utf-8"))
        text = "\\n\\n".join(blocks) if blocks else \\
            ctx.store.cleaned_text_path().read_text(encoding="utf-8")
        ctx.log.info("segment: 用了选中的 %d 个章节（%d 字）",
                     len(chosen), len(text))
    else:
        text = ctx.store.cleaned_text_path().read_text(encoding="utf-8")"""
    assert old3 in t, "segment 读文本锚点没找到"
    t = t.replace(old3, new3, 1)
    q.write_text(t, encoding="utf-8")
    print("segment.py: 按选中的章节分集")
