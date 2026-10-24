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
from ..models import Character, Status
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


def run(ctx: Context) -> dict:
    cfg = ctx.cfg.characters
    if not cfg.enabled:
        ctx.log.info("character: 已禁用，跳过")
        return {"skipped": True}
    chars = list(ctx.project.characters)
    if not chars:
        ctx.log.warning("character: 还没有角色（先跑 analyze）")
        return {"characters": 0, "refs": 0}
    if ctx.project.stage_status.get("character") == Status.DONE and \
            all(c.anchor_prompt or c.locked for c in chars):
        ctx.log.info("character: 已完成，跳过")
        return {"skipped": True}

    anchors = build_anchors(ctx, chars)
    refs = 0
    if cfg.generate_refs:
        refs = sum(generate_refs(ctx, c) for c in chars)
    ctx.save()
    ctx.project.stage_status["character"] = Status.DONE
    ctx.save()
    ctx.log.info("character: %d 个角色，锚点补齐 %d，参考图 %d",
                 len(chars), anchors, refs)
    return {"characters": len(chars), "anchors": anchors, "refs": refs}


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
