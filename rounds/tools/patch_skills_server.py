"""The console is told where the skills came from.

The selection the panel shows is the project's own - and the project
either chose them or had them recommended from the book.  The console
has to say which, so nobody wonders why a skill is ticked.

The recommendation itself is the shared one now: the analysis asks for
it when the project has no skills of its own, and the button asks for
it again when the book has changed.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\web\server.py")
text = PATH.read_text(encoding="utf-8")

# 1. the skills endpoint says where the selection came from
old = '''                costs = skillcat.cost(sel, getattr(cfg_skills, "refs", None))
                return self._json({"ok": True,
                                   "skills": skillcat.catalog(),
                                   "selection": sel,
                                   "costs": costs,
                                   "stages": list(stages)})'''
new = '''                costs = skillcat.cost(sel, getattr(cfg_skills, "refs", None))
                recommended = False
                if slug:
                    store0 = state.open_store(slug)
                    if store0:
                        recommended = bool(
                            (store0.load().meta.skills_recommended))
                return self._json({"ok": True,
                                   "skills": skillcat.catalog(),
                                   "selection": sel,
                                   "costs": costs,
                                   "recommended": recommended,
                                   "stages": list(stages)})'''
assert old in text, "没找到技能接口"
text = text.replace(old, new, 1)

# 2. saving by hand means the person chose them
old = '''            proj = store.load()
            proj.meta.skills = clean
            store.save(proj)
            return {"ok": True, "selection": clean,
                    "costs": skillcat.cost(clean, _cfg_refs(state))}'''
new = '''            proj = store.load()
            proj.meta.skills = clean
            # a person picked these, so they are no longer the ones the
            # book recommended
            proj.meta.skills_recommended = False
            store.save(proj)
            return {"ok": True, "selection": clean,
                    "costs": skillcat.cost(clean, _cfg_refs(state))}'''
assert old in text, "没找到保存技能"
text = text.replace(old, new, 1)

# 3. the recommendation is the shared one
i = text.index("        def _api_skills_recommend(self, body: dict) -> dict:")
j = text.index("\n        def ", i + 10) + 1
new_fn = '''        def _api_skills_recommend(self, body: dict) -> dict:
            """Which skills suit this project, and why.

            The same question the analysis asks when the project has no
            skills of its own - the catalogue's own words beside the
            project's genre, synopsis and cast.
            """
            slug = str(body.get("project") or "").strip()
            store = state.open_store(slug)
            if store is None:
                return {"ok": False, "error": "项目不存在"}
            from ..pipeline.runner import make_context
            from ..skills import recommend as _recommend
            ctx = make_context(state.cfg, store)
            got = _recommend.recommend(ctx)
            selection = got.get("selection") or {}
            if not selection:
                return {"ok": False, "error": "没有选出可用的技能"}
            reasons = got.get("reasons") or {}
            return {"ok": True, "selection": selection,
                    "reasons": {k: str(v) for k, v in reasons.items()}}
'''
text = text[:i] + new_fn + text[j:]

PATH.write_text(text, encoding="utf-8")
print("服务端改好了")
