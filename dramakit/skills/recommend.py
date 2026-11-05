"""Which skills suit this project.

The catalog says what each skill is for in its own words; the model
reads those beside the project's genre, synopsis and cast and answers.
Only names from the catalog come back - a model that invents a skill
would silently send nothing.

The answer is a recommendation, not a decision: it is what the project
starts with, and the person can take anything off it and add anything
back.
"""
from __future__ import annotations

import logging

log = logging.getLogger("dramakit.skills")

# the stages that write with skills
STAGES = ("analyze", "script", "storyboard", "promptgen")


def recommend(ctx) -> dict:
    """The skills that suit this project, and why.

    Returns {"selection": {...}, "reasons": {...}}.  An empty selection
    means the model could not be asked, and the project's own choices
    stand.
    """
    from . import catalog as skillcat

    proj = ctx.project
    skills = skillcat.catalog()
    if not skills:
        return {"selection": {}, "reasons": {}}

    lines = []
    for sk in skills:
        desc = (sk["description"] or "").replace("\n", " ")[:110]
        lines.append(f'- {sk["name"]} [{sk["family_zh"]}] '
                     f'({sk["chars"]}字): {desc}')
    chars = ", ".join(f"{c.name}({c.role})" for c in (proj.characters or [])[:12])
    ad = proj.art_direction
    synopsis = proj.meta.synopsis or ""
    if not synopsis:
        for s in (proj.seasons or []):
            if s.synopsis:
                synopsis = s.synopsis
                break
    ctx_txt = (f"项目: {proj.meta.title or proj.meta.name}\n"
               f"题材: {ad.genre} / {ad.style}\n"
               f"简介: {synopsis[:300]}\n"
               f"角色: {chars or '（尚未分析）'}\n"
               f"已选章节: {proj.meta.chosen_chapters}\n\n"
               f"可选技能（只能从下面的 name 里选）:\n"
               + "\n".join(lines))
    sys_prompt = (
        "你是短剧工厂的技能挑选助手。为这个项目挑选每个阶段该用的技能。\n"
        "只输出 JSON，格式：{\"analyze\": [skill name...], "
        "\"script\": [...], \"storyboard\": [...], "
        "\"promptgen\": [...], \"reasons\": {\"skill name\": \"一句中文理由\"}}\n"
        "规则：name 必须逐字来自清单；每个阶段至少选 1 个；"
        "与题材不符的不选（例：古装权谋不需要情景喜剧理论）；"
        "宁可少选也不要全选——技能越多每次调用越慢。")
    try:
        llm = ctx.providers.llm_for("actions")
        data = llm.complete_json(sys_prompt, ctx_txt)
    except Exception as e:  # noqa: BLE001
        log.warning("skills: 推荐失败(%s)", str(e)[:160])
        return {"selection": {}, "reasons": {}}
    if isinstance(data, list):
        data = data[0] if data else {}
    have = {sk["name"] for sk in skills}
    selection: dict[str, list[str]] = {}
    for stage in STAGES:
        got = data.get(stage) or []
        keep = [str(n) for n in got if str(n) in have]
        if keep:
            selection[stage] = keep
    reasons = {str(k): str(v) for k, v in (data.get("reasons") or {}).items()
               if str(k) in have}
    if not selection:
        log.warning("skills: 模型没有选出可用的技能")
        return {"selection": {}, "reasons": {}}
    return {"selection": selection, "reasons": reasons}
