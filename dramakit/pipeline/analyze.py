"""Stage 2 — analyze: extract characters, locations and art direction via LLM.

Long novels are sampled (head + chapter openings + tail) to fit the model's
context while still catching the main cast and world.
"""
from __future__ import annotations

import json

from ..models import ArtDirection, Character, Location
from ..prompts import templates as T
from .base import Context

MAX_ANALYZE_CHARS = 14000


def _sample(text: str, chapters: list[dict]) -> str:
    if len(text) <= MAX_ANALYZE_CHARS:
        return text
    head = text[: MAX_ANALYZE_CHARS // 2]
    # sprinkle chapter openings from the middle
    mids: list[str] = []
    step = max(1, len(chapters) // 8)
    for ch in chapters[::step]:
        body = (ch.get("body") or "")[:600]
        if body:
            mids.append(f"【{ch.get('title','')}】\n{body}")
    mid_text = "\n\n".join(mids)[: MAX_ANALYZE_CHARS // 3]
    tail = text[-1500:]
    return f"{head}\n\n...【中段节选】...\n{mid_text}\n\n...【结尾节选】...\n{tail}"


def run(ctx: Context) -> dict:
    if ctx.project.characters and ctx.project.stage_status.get("analyze") == "done":
        ctx.log.info("analyze: 已完成，跳过（%d 角色）", len(ctx.project.characters))
        return {"skipped": True}

    text = ctx.store.cleaned_text_path().read_text(encoding="utf-8")
    chapters = json.loads(ctx.store.chapters_path().read_text(encoding="utf-8")) \
        if ctx.store.chapters_path().exists() else []
    sample = _sample(text, chapters)

    llm = ctx.providers.llm_for("analyze")
    user = T.render(T.ANALYZE_USER, text=sample, max_characters=12, max_locations=10)
    data = llm.complete_json(T.ANALYZE_SYSTEM, user)
    if isinstance(data, list):
        data = data[0] if data else {}

    # art direction
    ad = data.get("art_direction", {}) or {}
    base = ctx.project.art_direction
    ctx.project.art_direction = ArtDirection(
        genre=data.get("genre") or base.genre,
        style=ad.get("style") or base.style,
        aspect_ratio=base.aspect_ratio,
        era=ad.get("era") or base.era,
        color_palette=ad.get("color_palette") or base.color_palette,
        global_negative_prompt=base.global_negative_prompt,
        style_prompt_prefix=base.style_prompt_prefix,
    )

    # characters
    chars: list[Character] = []
    for c in data.get("characters", []) or []:
        if not c.get("name"):
            continue
        chars.append(Character(
            name=str(c["name"]).strip(),
            aliases=[str(a) for a in (c.get("aliases") or [])],
            role=c.get("role", "配角"),
            gender=c.get("gender", "未知"),
            age=str(c.get("age", "")),
            personality=c.get("personality", ""),
            appearance=c.get("appearance", ""),
            visual_prompt=c.get("visual_prompt", ""),
        ))
    ctx.project.characters = chars

    # locations
    locs = [Location(name=str(l["name"]).strip(), description=l.get("description", ""),
                     visual_prompt=l.get("visual_prompt", ""))
            for l in (data.get("locations") or []) if l.get("name")]
    ctx.project.locations = locs

    if data.get("title") and not ctx.project.meta.title:
        ctx.project.meta.title = data["title"]
    if data.get("synopsis"):
        ctx.project.meta.synopsis = data["synopsis"]
    if data.get("genre"):
        ctx.project.art_direction.genre = data["genre"]

    ctx.project.stage_status["analyze"] = "done"
    ctx.save()
    ctx.log.info("analyze: 《%s》%s | %d 角色, %d 场景",
                 ctx.project.meta.title, ctx.project.art_direction.genre,
                 len(chars), len(locs))
    return {"characters": len(chars), "locations": len(locs)}
