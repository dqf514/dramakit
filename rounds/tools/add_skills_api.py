"""The skills become something a person can see, choose, and ask about.

The list of rules each stage writes with lived in a YAML file, which meant
the only way to find out what a stage was sending was to read the code -
and the only way to change it was to edit configuration and restart. A
page cannot restart a run, and a person choosing between twenty-six
screenwriting theories should be able to read what each one is for.

Three endpoints. The catalog, so the page can list what exists and what
each would cost in characters. A save, which writes the choice onto the
project - two dramas that share a genre word need not share their rules.
And a recommendation: the model reads the project's genre, synopsis and
cast, and says which skills suit it, with a reason for each, so the
thirty-seven choices are not thirty-seven guesses.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

if '"/api/skills"' in s:
    print("server.py: 技能接口已存在，跳过")
    raise SystemExit(0)

# ------------------------------------------------------- the routes -----
old_get = '''            if path == "/api/logs":'''
new_get = '''            if path == "/api/skills":
                from ..skills import catalog as skillcat
                slug = (query.get("project") or [""])[0]
                sel, costs = {}, {}
                if slug:
                    store = state.open_store(slug)
                    if store:
                        proj = store.load()
                        sel = proj.meta.skills or {}
                from ..config import Config as _C
                cfg_skills = _C.load(state.config_path).skills
                if not sel:
                    # nothing chosen for this project: what the config says
                    sel = {k: list(getattr(cfg_skills, k) or [])
                           for k in ("analyze", "script", "storyboard", "promptgen")}
                costs = skillcat.cost(sel)
                return self._json({"ok": True,
                                   "skills": skillcat.catalog(),
                                   "selection": sel,
                                   "costs": costs,
                                   "stages": ["analyze", "script",
                                              "storyboard", "promptgen"]})
            if path == "/api/logs":'''
assert old_get in s, "/api/logs 路由锚点没找到"
s = s.replace(old_get, new_get, 1)

old_post = '''            if path == "/api/jobs/stop":'''
new_post = '''            if path == "/api/skills/save":
                return self._json(self._api_skills_save(body))
            if path == "/api/skills/recommend":
                return self._json(self._api_skills_recommend(body))
            if path == "/api/jobs/stop":'''
assert old_post in s, "/api/jobs/stop 路由锚点没找到"
s = s.replace(old_post, new_post, 1)

# --------------------------------------------------- the handlers -------
anchor = "        def _api_run(self, body: dict) -> dict:"
assert anchor in s, "_api_run 锚点没找到"

handlers = '''        def _api_skills_save(self, body: dict) -> dict:
            """Write this project's skill choices.

            Onto the project, not the config: a choice made for one drama
            should not change the next one, and a run that is going cannot
            be restarted to pick up a config edit anyway.
            """
            slug = str(body.get("project") or "").strip()
            store = state.open_store(slug)
            if not store:
                return {"ok": False, "error": "项目不存在"}
            sel = body.get("selection")
            if not isinstance(sel, dict):
                return {"ok": False, "error": "selection 必须是对象"}
            from ..skills import catalog as skillcat
            have = {s["name"] for s in skillcat.catalog()}
            clean: dict[str, list[str]] = {}
            for stage in ("analyze", "script", "storyboard", "promptgen"):
                if stage not in sel:
                    continue
                names = sel.get(stage) or []
                if not isinstance(names, list):
                    return {"ok": False, "error": f"{stage} 必须是列表"}
                # only what exists: a name from a deleted skill would be
                # silently dropped at load time, and better said here
                clean[stage] = [n for n in names if str(n) in have]
            proj = store.load()
            proj.meta.skills = clean
            store.save(proj)
            return {"ok": True, "selection": clean,
                    "costs": skillcat.cost(clean)}

        def _api_skills_recommend(self, body: dict) -> dict:
            """Which skills suit this project, and why.

            The catalog says what each skill is for in its own words; the
            model reads those beside the project's genre, synopsis and
            cast and answers. Only names from the catalog come back - a
            model that invents a skill would silently send nothing.
            """
            slug = str(body.get("project") or "").strip()
            store = state.open_store(slug)
            if not store:
                return {"ok": False, "error": "项目不存在"}
            proj = store.load()
            from ..skills import catalog as skillcat
            skills = skillcat.catalog()

            lines = []
            for sk in skills:
                desc = (sk["description"] or "").replace("\\n", " ")[:110]
                lines.append(f'- {sk["name"]} [{sk["family_zh"]}] '
                             f'({sk["chars"]}字): {desc}')
            chars = ", ".join(f"{c.name}({c.role})"
                              for c in (proj.characters or [])[:12])
            ad = proj.art_direction
            ctx_txt = (f"项目: {proj.meta.title or proj.meta.name}\\n"
                       f"题材: {ad.genre} / {ad.style}\\n"
                       f"简介: {(proj.meta.synopsis or '')[:300]}\\n"
                       f"角色: {chars or '（尚未分析）'}\\n"
                       f"已选章节: {proj.meta.chosen_chapters}\\n\\n"
                       f"可选技能（只能从下面的 name 里选）:\\n"
                       + "\\n".join(lines))
            sys_prompt = (
                "你是短剧工厂的技能挑选助手。为这个项目挑选每个阶段该用的技能。\\n"
                "只输出 JSON，格式：{\\"analyze\\": [skill name...], "
                "\\"script\\": [...], \\"storyboard\\": [...], "
                "\\"promptgen\\": [...], \\"reasons\\": {\\"skill name\\": \\"一句中文理由\\"}}\\n"
                "规则：name 必须逐字来自清单；每个阶段至少选 1 个；"
                "与题材不符的不选（例：古装权谋不需要情景喜剧理论）；"
                "宁可少选也不要全选——技能越多每次调用越慢。")
            try:
                brain = state.brain()
                data = brain.json(sys_prompt, ctx_txt, role="skills",
                                  temperature=0.2)
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": f"推荐失败: {str(e)[:200]}"}
            if isinstance(data, list):
                data = data[0] if data else {}
            if not isinstance(data, dict):
                return {"ok": False, "error": "模型没有返回对象"}

            have = {sk["name"] for sk in skills}
            clean: dict[str, list[str]] = {}
            for stage in ("analyze", "script", "storyboard", "promptgen"):
                got = data.get(stage) or []
                if not isinstance(got, list):
                    continue
                keep = [str(n) for n in got if str(n) in have]
                if keep:
                    clean[stage] = keep
            if not clean:
                return {"ok": False, "error": "模型没有选出可用的技能"}
            reasons = data.get("reasons") or {}
            if not isinstance(reasons, dict):
                reasons = {}
            return {"ok": True, "selection": clean,
                    "reasons": {k: str(v) for k, v in reasons.items()},
                    "costs": skillcat.cost(clean)}

'''
s = s.replace(anchor, handlers + anchor, 1)

p.write_text(s, encoding="utf-8")
print("server.py: /api/skills + save + recommend")
