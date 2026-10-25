"""Stage 3 — character: lock every character's look before storyboarding.

Produces two things that the downstream stages reuse verbatim:
  * `anchor_prompt` — a stable English block (face, hair, outfit) injected at the
    front of every shot prompt
  * reference images — front / side / three-quarter portraits generated with a
    per-character fixed seed, so a human can eyeball and lock the cast

If ComfyUI is off or unreachable the anchors are still written, so prompt-only
consistency keeps working.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import Config
from ..models import Character, Location, Status
from ..project import ProjectStore
from ..prompts import templates as T
from .base import Context

VIEW_TEXT = {
    "front": "front view, facing the camera, neutral standing pose",
    "side": "side profile view, facing left, neutral standing pose",
    "three_quarter": "three-quarter view, slight body angle, neutral standing pose",
}


def _seed(name: str, view: str) -> int:
    digest = hashlib.sha1(f"{name}:{view}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % (2**31)


def _fallback_anchor(c: Character) -> str:
    bits = [c.visual_prompt or c.appearance, c.hair, c.outfit]
    return ", ".join(b.strip().rstrip(",") for b in bits if b and b.strip())


def build_anchors(ctx: Context, chars: list[Character]) -> int:
    """Fill missing anchor prompts (LLM first, deterministic fallback second)."""
    if not chars:
        return 0
    cfg = ctx.cfg.characters
    before = sum(1 for c in chars if c.anchor_prompt)
    pending = [c for c in chars if not c.anchor_prompt and not c.locked]
    if pending and cfg.use_llm_anchor:
        lines = "\n".join(
            f"- name: {c.name}; role: {c.role}; gender: {c.gender}; age: {c.age}; "
            f"appearance: {c.appearance}; visual_prompt: {c.visual_prompt}; "
            f"outfit: {c.outfit}; hair: {c.hair}; locked: {c.locked}"
            for c in pending)
        try:
            llm = ctx.providers.llm_for("promptgen")
            data = llm.complete_json(
                T.CHARACTER_SHEET_SYSTEM,
                T.render(T.CHARACTER_SHEET_USER, characters=lines,
                         max_chars=cfg.anchor_max_chars))
            if isinstance(data, list):
                data = {"characters": data}
            by_name = {str(x.get("name", "")).strip(): x
                       for x in (data.get("characters") or []) if isinstance(x, dict)}
            for c in pending:
                item = by_name.get(c.name)
                if not item:
                    continue
                anchor = str(item.get("anchor_prompt") or "").strip()
                if anchor:
                    c.anchor_prompt = anchor[: cfg.anchor_max_chars]
                neg = str(item.get("negative_prompt") or "").strip()
                if neg:
                    c.negative_prompt = neg
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("character: 角色锚点 LLM 失败(%s)，用设定兜底", str(e)[:160])
    made = 0
    for c in chars:
        if not c.anchor_prompt:
            c.anchor_prompt = _fallback_anchor(c)[: cfg.anchor_max_chars]
            made += 1
    return max(made, sum(1 for c in chars if c.anchor_prompt) - before)


def _ref_prompt(ctx: Context, c: Character, view: str) -> str:
    ad = ctx.project.art_direction
    style = ad.style_prompt_prefix or ad.style or "cinematic realistic"
    return (
        f"character reference sheet, {c.anchor()}, "
        f"{VIEW_TEXT.get(view, VIEW_TEXT['front'])}, full body, "
        f"plain light gray studio background, soft even lighting, "
        f"{style}, highly detailed, no text, no watermark"
    )


def _loc_prompt(ctx: Context, loc: Location) -> str:
    ad = ctx.project.art_direction
    style = ad.style_prompt_prefix or ad.style or "cinematic realistic"
    desc = loc.visual_prompt or loc.description or loc.name
    return (
        f"location reference photo, empty scene, {desc}, "
        f"no people, no text, no watermark, {ad.era}, {style}, "
        f"wide establishing view, consistent architecture, highly detailed"
    )


def generate_location_refs(ctx: Context) -> int:
    """Generate one establishing reference image per location. Never raises."""
    cfg = ctx.cfg.characters
    vis = ctx.providers.visual
    if vis is None or not ctx.project.locations:
        return 0
    if hasattr(vis, "ping") and not vis.ping():
        ctx.log.warning("character: ComfyUI 不可达，跳过场景参考图")
        return 0
    ccfg = ctx.cfg.comfyui
    negative = "people, person, crowd, text, watermark, logo, blurry, distorted"
    made = 0
    for loc in ctx.project.locations:
        existing = [r for r in loc.ref_images
                    if ctx.store.abs(r).exists()]
        if existing:
            loc.ref_images = existing
            continue
        out = ctx.store.location_ref_path(loc.name)
        try:
            vis.generate_image(
                prompt=_loc_prompt(ctx, loc), negative=negative,
                width=cfg.ref_width, height=cfg.ref_height,
                seed=_seed("loc:" + loc.name, "ref"), steps=ccfg.steps, cfg=ccfg.cfg,
                out_path=str(out),
                extra={"sampler": ccfg.sampler, "scheduler": ccfg.scheduler,
                       "checkpoint": ccfg.checkpoint})
            rel = ctx.store.rel(out)
            loc.ref_images = [rel]
            made += 1
            ctx.log.info("character: 场景 %s 参考图已生成", loc.name)
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("character: 场景 %s 出图失败 %s", loc.name, str(e)[:160])
    return made


def generate_refs(ctx: Context, c: Character, views: list[str] | None = None) -> int:
    """Generate reference portraits for one character. Never raises."""
    cfg = ctx.cfg.characters
    vis = ctx.providers.visual
    if vis is None:
        ctx.log.info("character: 未启用画面 provider，跳过 %s 的三视图", c.name)
        return 0
    if hasattr(vis, "ping") and not vis.ping():
        ctx.log.warning("character: ComfyUI 不可达，跳过 %s 的三视图", c.name)
        return 0
    views = views or cfg.ref_views or ["front"]
    ccfg = ctx.cfg.comfyui
    negative = ", ".join(x for x in (c.negative_prompt,
                                     "different person, inconsistent face, extra limbs, text, watermark")
                         if x)
    made = 0
    for view in views:
        out = ctx.store.character_ref_path(c.name, view, "png")
        try:
            vis.generate_image(
                prompt=_ref_prompt(ctx, c, view), negative=negative,
                width=cfg.ref_width, height=cfg.ref_height,
                seed=_seed(c.name, view), steps=ccfg.steps, cfg=ccfg.cfg,
                out_path=str(out),
                extra={"sampler": ccfg.sampler, "scheduler": ccfg.scheduler,
                       "checkpoint": ccfg.checkpoint})
            rel = ctx.store.rel(out)
            if rel not in c.ref_images:
                c.ref_images.append(rel)
            if not c.ref_sheet:
                c.ref_sheet = rel
            made += 1
            ctx.log.info("character: %s %s 参考图已生成", c.name, view)
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("character: %s %s 出图失败 %s", c.name, view, str(e)[:160])
    return made


def _fallback_voice(c: Character, voices: list[str]) -> str:
    if not voices:
        return ""
    female = ("女", "female")
    male = ("男", "male")
    prefs = []
    if c.gender in female:
        prefs = ["Xiaoxiao", "Xiaoyi", "Xiaochen", "Xiaohan", "Xiaomeng",
                 "Xiaomo", "Xiaoxuan", "Xiaoyan"]
    elif c.gender in male:
        prefs = ["Yunxi", "Yunjian", "Yunye", "Yunyang", "Yunfeng", "Yunhao"]
    for name in prefs:
        for voice in voices:
            if name.lower() in voice.lower():
                return voice
    return voices[0]


# 标准普通话音色的气质备注：喂给配音导演 LLM，让它按年龄/气质挑
VOICE_NOTES: dict[str, str] = {
    "zh-CN-YunxiNeural": "青年男声，阳光清朗，适合男主/少年",
    "zh-CN-YunjianNeural": "青年男声，硬朗有力，适合硬汉/战神/狠角色",
    "zh-CN-YunxiaNeural": "少年男声，稚气，适合弟弟/学生",
    "zh-CN-YunyangNeural": "成年男声，成熟稳重有分量，适合长辈/反派/老板",
    "zh-CN-XiaoxiaoNeural": "青年女声，温柔标准，适合女主",
    "zh-CN-XiaoyiNeural": "少女女声，甜美活泼，适合少女/甜宠",
}

# 内置兜底音色池：provider 音色表拉取失败时用（edge-tts 偶尔被网络抖动打空）
FALLBACK_VOICES: list[str] = [
    "zh-CN-YunxiNeural", "zh-CN-YunjianNeural", "zh-CN-YunxiaNeural",
    "zh-CN-YunyangNeural", "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural",
]


def _curated_voices(ctx: Context, voices: list[str]) -> tuple[list[str], str]:
    """Filter the provider voice list down to a usable, annotated pool.

    Keeps only the configured locales (default: standard Mandarin, no dialects)
    so the casting LLM cannot pick a Cantonese/Taiwanese voice for a mainland
    drama, and annotates each voice with its age/timbre.
    """
    cfg = ctx.cfg.tts
    pool = [v for v in voices if v not in set(cfg.voice_exclude or [])]
    if cfg.voice_pool:
        allowed = set(cfg.voice_pool)
        pool = [v for v in pool if v in allowed]
    else:
        locs = cfg.voice_locales or ["zh-CN"]
        pool = [v for v in pool
                if any(v.startswith(f"{loc}-") and len(v.split("-")) == 3 for loc in locs)]
    notes = {**VOICE_NOTES, **(cfg.voice_notes or {})}
    listed = "\n".join(f"- {v}" + (f"   # {notes[v]}" if v in notes else "")
                       for v in pool)
    return pool, listed


def cast_voices(ctx: Context, chars: list[Character]) -> int:
    """Assign a TTS voice to every character without one (LLM, then gender map)."""
    cfg = ctx.cfg.characters
    if not cfg.auto_cast:
        return 0
    pending = [c for c in chars if not c.voice_id]
    if not pending:
        return 0
    try:
        voices = ctx.providers.tts.list_voices()
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("character: 读取音色失败(%s)，改用内置兜底音色池", str(e)[:120])
        voices = []
    voices, voices_doc = _curated_voices(ctx, voices)
    if not voices:
        # provider 音色表为空（网络抖动/服务不可用）：退回内置池，别让整集选角失败
        voices, voices_doc = _curated_voices(ctx, FALLBACK_VOICES)
        ctx.log.warning("character: 音色表不可用，使用内置兜底音色池")
    if not voices:
        return 0
    lines = "\n".join(
        f"- name: {c.name}; role: {c.role}; gender: {c.gender}; age: {c.age}; "
        f"personality: {c.personality}" for c in pending)
    ad = ctx.project.art_direction
    try:
        llm = ctx.providers.llm_for("script")
        data = llm.complete_json(
            T.VOICE_CAST_SYSTEM,
            T.render(T.VOICE_CAST_USER, characters=lines, voices=voices_doc,
                     genre=ad.genre or "", style=ad.style or "", era=ad.era or "",
                     tone=ad.color_palette or ""))
        if isinstance(data, list):
            data = {"characters": data}
        by_name = {str(x.get("name", "")).strip(): x
                   for x in (data.get("characters") or []) if isinstance(x, dict)}
        for c in pending:
            got = by_name.get(c.name, {})
            picked = str(got.get("voice_id", "")).strip()
            if picked in voices:
                c.voice_id = picked
                c.voice_pitch = str(got.get("pitch", "")).strip()
                c.voice_rate = str(got.get("rate", "")).strip()
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("character: 自动选角 LLM 失败(%s)，按性别兜底", str(e)[:120])
    made = 0
    for c in pending:
        if not c.voice_id:
            c.voice_id = _fallback_voice(c, voices)
        made += bool(c.voice_id)
    return made


def run(ctx: Context) -> dict:
    cfg = ctx.cfg.characters
    if not cfg.enabled:
        ctx.log.info("character: 已禁用，跳过")
        return {"skipped": True}
    chars = list(ctx.project.characters)
    if not chars:
        ctx.log.warning("character: 还没有角色（先跑 analyze）")
        return {"characters": 0, "refs": 0}
    anchors_ready = all(c.anchor_prompt or c.locked for c in chars)
    refs_ready = (not cfg.generate_refs) or all(
        any(ctx.store.abs(r).exists() for r in c.refs()) for c in chars)
    locs_ready = (not cfg.generate_location_refs) or all(
        any(ctx.store.abs(r).exists() for r in l.ref_images)
        for l in ctx.project.locations)
    cast_ready = (not cfg.auto_cast) or all(c.voice_id for c in chars)
    if ctx.project.stage_status.get("character") == Status.DONE and \
            anchors_ready and refs_ready and locs_ready and cast_ready:
        ctx.log.info("character: 已完成，跳过")
        return {"skipped": True}

    anchors = build_anchors(ctx, chars)
    casted = cast_voices(ctx, chars)
    refs = 0
    if cfg.generate_refs:
        refs = sum(generate_refs(ctx, c) for c in chars)
    loc_refs = generate_location_refs(ctx) if cfg.generate_location_refs else 0
    ctx.save()
    ctx.project.stage_status["character"] = Status.DONE
    ctx.save()
    ctx.log.info("character: %d 个角色，锚点补齐 %d，选角 %d，参考图 %d，场景参考图 %d",
                 len(chars), anchors, casted, refs, loc_refs)
    return {"characters": len(chars), "anchors": anchors, "cast": casted,
            "refs": refs, "location_refs": loc_refs}


def generate_for_one(store: ProjectStore, cfg: Config, name: str,
                     views: list[str] | None = None) -> dict:
    """API entry: refresh one character's anchor and reference images."""
    ctx = Context(cfg, store)
    char = ctx.project.character(name)
    if char is None:
        return {"ok": False, "error": f"没有角色：{name}"}
    build_anchors(ctx, [char])
    refs = generate_refs(ctx, char, views) if cfg.characters.generate_refs else 0
    ctx.save()
    return {"ok": True, "name": char.name, "anchor_prompt": char.anchor_prompt,
            "refs": refs, "ref_images": char.refs(), "ref_sheet": char.ref_sheet}
