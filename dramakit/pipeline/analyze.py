"""Stage 2 — analyze: read this season's chapters, extract cast and art direction.

A long novel is not analyzed once at the start and never again. It is
analyzed one season at a time, because reading the whole book up front
costs time the user does not have, and because a character does not look
the same in chapter 40 as they did in chapter 1 - they grow up, change
sides, gain power, get scarred. What the story *is* has to be read from
the chapters this season is made from.

Continuity comes from the canon, not from re-reading the book. The canon
is what carried across the seasons already made: who each character is,
how each has looked so far, and where the story left off. analyze reads
it, so it knows 余飞 was already a tree by the end of last season, and can
decide what has changed since. Identity and voice are carried through
unchanged; the look is this season's to decide.

A character that arrives with the same name keeps their voice and their
place in the cast, and gets a look that may differ from last season's -
the story is allowed to have moved them. Locked characters are the
exception: a locked look is not rewritten by analysis, only by the user.
"""
from __future__ import annotations

import json

from ..models import ArtDirection, Character, Location, Prop
from ..prompts import templates as T
from ..seasons import (LOOK_FIELDS, apply_look, character_digest,
                       record_season_looks)
from .base import Context

MAX_ANALYZE_CHARS = 14000


def _season_text(ctx: Context) -> tuple[str, list[dict]]:
    """The text of the chapters this season is made from.

    A season is made from a chosen slice of the book, so that is what gets
    read - not the whole novel. When no chapters are picked (a project
    made before season picking existed) the whole book is the input.
    """
    indices = ctx.season_chapters()
    if not indices:
        text = ctx.store.cleaned_text_path().read_text(encoding="utf-8")
        chapters = json.loads(ctx.store.chapters_path().read_text(encoding="utf-8")) \
            if ctx.store.chapters_path().exists() else []
        return text, chapters

    meta = ctx.project.meta
    by_index = {c.index: c for c in (meta.chapters or [])}
    parts: list[str] = []
    chapter_dicts: list[dict] = []
    for idx in sorted(indices):
        c = by_index.get(idx)
        if not c or not c.file:
            continue
        f = ctx.store.root / c.file
        if not f.exists():
            continue
        body = f.read_text(encoding="utf-8")
        parts.append(body)
        chapter_dicts.append({"title": c.title or f"第{idx}章", "body": body})
    return "\n\n".join(parts), chapter_dicts


def _canon_block(ctx: Context) -> str:
    """What the seasons before this one already established.

    This is the whole mechanism for continuity: it tells the analysis who
    these people already are and where the story has got to, so the new
    season can be continuous without re-reading the book. It is kept short
    on purpose - the canon is a digest, not a transcript.
    """
    canon = ctx.project.canon
    lines: list[str] = []
    done = sorted(set(canon.done_chapters or []))
    if done:
        lines.append(f"已制作章节：第 {done[0]} ~ 第 {done[-1]} 章（共 {len(done)} 章）。")
    if canon.progress:
        lines.append(f"剧情进度：{canon.progress}")
    dig = character_digest(_canon_characters(ctx))
    if dig:
        lines.append("已出场人物：\n" + dig)
    # An art direction is only history once a season has been made with it.
    # A new project's canon already holds the defaults the store seeded, and
    # quoting those back would tell the first season that its own look was
    # decided before it was asked.
    if (canon.art_direction.genre or canon.art_direction.style) and done:
        lines.append(f"美术方向沿用：{canon.art_direction.genre} / "
                     f"{canon.art_direction.style}")
    if not lines:
        return ""
    return ("以下是此前已制作内容的设定摘要，用于保持连续性。"
            "人物的身份与声音不变，但外貌可随剧情发展而改变：\n"
            + "\n".join(lines))


def _canon_characters(ctx: Context) -> list[Character]:
    """The cast as the canon remembers it, for the continuity digest.

    Only the canon counts here. The live cast is deliberately not a
    fallback: in the first season the canon is empty and the live cast is
    this season's own analysis, so falling back would tell the model that
    the story it is about to read has already happened - and season 2 would
    read its own cast as prior history rather than as the people it is
    introducing. An empty canon means there is no history, and that is the
    truth the preamble has to tell.
    """
    canon = ctx.project.canon
    out = []
    for name, data in canon.characters.items():
        c = Character(name=name)
        for k, v in (data or {}).items():
            if hasattr(c, k):
                setattr(c, k, v)
        # the most recent look, so the digest shows who they are now
        looks = canon.character_looks.get(name) or []
        if looks:
            apply_look(c, looks[-1])
        out.append(c)
    return out


def run(ctx: Context) -> dict:
    season = ctx.seed_season(ctx.season_chapters()
                             or list(ctx.project.meta.chosen_chapters or []))
    # A resume must not read the same chapters again. The analysis is the
    # one stage whose output is a decision - who is in the cast, what they
    # look like - and running it twice on the same pages is a second
    # opinion nobody asked for, which then overwrites the first.
    if season is not None and season.stage_status.get("analyze") == "done" \
            and (ctx.project.characters or ctx.project.locations):
        ctx.log.info("analyze: 第%d季已分析过，跳过（%d 角色）",
                     season.index, len(ctx.project.characters))
        return {"skipped": True, "season": season.index,
                "characters": len(ctx.project.characters),
                "locations": len(ctx.project.locations)}
    text, chapters = _season_text(ctx)
    if not text.strip():
        ctx.log.warning("analyze: 本季没有可读的章节文本")
        return {"characters": 0, "locations": 0, "season": season.index}

    sample = _sample(text, chapters)
    canon_block = _canon_block(ctx)

    ctx.check_stop()
    llm = ctx.providers.llm_for("analyze")
    from ..skills import loader
    user = T.render(T.ANALYZE_USER, text=sample, max_characters=12,
                    max_locations=10, max_props=8) + loader.for_stage(ctx, "analyze")
    if canon_block:
        user = canon_block + "\n\n" + user
    data = llm.complete_json(T.ANALYZE_SYSTEM, user)
    if isinstance(data, list):
        data = data[0] if data else {}

    ctx.check_stop()
    # art direction: this season's, falling back to what the canon holds
    ad = data.get("art_direction", {}) or {}
    base = ctx.project.art_direction
    # A look the user chose is the look of the whole drama: the analysis
    # may read the book and say what kind of story it is, but it does not
    # get to change the picture the user asked for.
    locked = bool((base.style_prompt_prefix or "").strip())
    ctx.project.art_direction = ArtDirection(
        genre=data.get("genre") or base.genre,
        style=(base.style if locked else (ad.get("style") or base.style)),
        aspect_ratio=base.aspect_ratio,
        frame_width=base.frame_width,
        frame_height=base.frame_height,
        era=ad.get("era") or base.era,
        color_palette=ad.get("color_palette") or base.color_palette,
        global_negative_prompt=base.global_negative_prompt,
        style_prompt_prefix=base.style_prompt_prefix,
    )

    # characters: who they are travels through, how they look is this
    # season's to decide - unless the look is locked, which is the user's
    # and not the analysis's to change.
    chars = _merge_characters(ctx, data.get("characters") or [])
    ctx.project.characters = chars
    # write this season's cast into the canon, so the season after it
    # inherits who these people are and how each has looked
    record_season_looks(ctx.project.canon, season.index, chars)

    locs = [Location(name=str(l["name"]).strip(), description=l.get("description", ""),
                     visual_prompt=l.get("visual_prompt", ""))
            for l in (data.get("locations") or []) if l.get("name")]
    ctx.project.locations = _merge_locations(ctx, locs)
    ctx.project.props = _merge_props(ctx, [
        Prop(name=str(p["name"]).strip(),
             description=p.get("description", ""),
             visual_prompt=p.get("visual_prompt", ""))
        for p in (data.get("props") or []) if p.get("name")])

    if data.get("title") and not ctx.project.meta.title:
        ctx.project.meta.title = data["title"]
    if data.get("synopsis"):
        season.synopsis = str(data["synopsis"])
    if data.get("genre"):
        ctx.project.art_direction.genre = data["genre"]

    season.stage_status["analyze"] = "done"
    ctx.project.stage_status["analyze"] = "done"
    ctx.save()
    ctx.log.info("analyze: 第%d季 《%s》%s | %d 角色, %d 场景",
                 season.index, ctx.project.meta.title,
                 ctx.project.art_direction.genre, len(chars), len(ctx.project.locations))
    return {"characters": len(chars), "locations": len(ctx.project.locations),
            "season": season.index}


def _merge_characters(ctx: Context, found: list[dict]) -> list[Character]:
    """The cast for this season, in continuity with the seasons before it.

    A character that arrives with a name we already know keeps who they
    are - their role, their voice, their place in the cast - because those
    are what make them the same person across a long story. What they look
    like is this season's to decide: the story may have moved them on from
    how they looked when we last saw them.

    A locked character is the exception. A locked look is the user's
    decision, not the analysis's, so it is carried through untouched and
    only the user can change it.
    """
    prev = {c.name: c for c in ctx.project.characters}
    canon = ctx.project.canon
    out: list[Character] = []
    for raw in found:
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        c = Character(
            name=name,
            aliases=[str(a) for a in (raw.get("aliases") or [])],
            role=raw.get("role", "配角"),
            gender=raw.get("gender", "未知"),
            age=str(raw.get("age", "")),
            personality=raw.get("personality", ""),
            appearance=raw.get("appearance", ""),
            visual_prompt=raw.get("visual_prompt", ""),
        )
        old = prev.get(name)
        if old is not None:
            # Voice and identity are what make them the same person, and
            # so is everything already decided about them: the recording
            # made at 定妆, the pictures already drawn, the anchor that
            # keeps the face the same. The files stay on disk either way,
            # but a field left empty makes the next stage see a character
            # with no pictures and draw them again.
            c.voice_id = old.voice_id
            c.voice_pitch = old.voice_pitch
            c.voice_rate = old.voice_rate
            c.voice_ref = old.voice_ref
            c.ref_images = list(old.ref_images or [])
            c.ref_sheet = old.ref_sheet
            c.ref_image = old.ref_image
            c.anchor_prompt = old.anchor_prompt
            c.negative_prompt = old.negative_prompt
            c.consistency = old.consistency
            c.lora = old.lora
            c.locked = old.locked
            if not c.role or c.role == "配角":
                c.role = old.role
            if not c.appearance:
                c.appearance = old.appearance
            if not c.visual_prompt:
                c.visual_prompt = old.visual_prompt
        else:
            # a name the canon knows but this season's pages did not return
            c.voice_id = canon.voices.get(name, "")
        out.append(c)

    # A character the analysis no longer mentions is still in the story.
    # The pages this season read may not have reached them, and dropping
    # them would take their voice, their pictures and their anchor with
    # them - the next stage would then draw the same person again.
    for name, old in prev.items():
        if any(c.name == name for c in out):
            continue
        out.append(old)
        ctx.log.info("analyze: %s 这季没出现，保留其设定", name)
    return out


def _merge_locations(ctx: Context, found: list[Location]) -> list[Location]:
    """Locations keep their reference images across seasons.

    A place does not usually change between one season and the next, so a
    location we have already drawn keeps its references rather than being
    drawn again from scratch.
    """
    prev = {l.name: l for l in ctx.project.locations}
    for loc in found:
        old = prev.get(loc.name)
        if old is not None:
            loc.ref_images = list(old.ref_images)
    return found


def _merge_props(ctx: Context, found: list[Prop]) -> list[Prop]:
    """Props keep their reference sheets across seasons, like locations."""
    prev = {p.name: p for p in ctx.project.props}
    for prop in found:
        old = prev.get(prop.name)
        if old is not None:
            prop.ref_images = list(old.ref_images)
            prop.ref_sheet = old.ref_sheet
    return found


def _sample(text: str, chapters: list[dict]) -> str:
    if len(text) <= MAX_ANALYZE_CHARS:
        return text
    head = text[: MAX_ANALYZE_CHARS // 2]
    mids: list[str] = []
    step = max(1, len(chapters) // 8)
    for ch in chapters[::step]:
        body = (ch.get("body") or "")[:600]
        if body:
            mids.append(f"【{ch.get('title','')}】\n{body}")
    mid_text = "\n\n".join(mids)[: MAX_ANALYZE_CHARS // 3]
    tail = text[-1500:]
    return f"{head}\n\n...【中段节选】...\n{mid_text}\n\n...【结尾节选】...\n{tail}"
