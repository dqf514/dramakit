"""Stage 1 — ingest: read the novel/script, clean it, detect chapters.

Outputs (persisted to source/):
  cleaned.txt    full normalized text
  chapters.json  [{title, body}]
Also records basic meta on the project.
"""
from __future__ import annotations

import json

from ..utils.text import clean, read_source, split_chapters
from .base import Context


def run(ctx: Context, source_file: str | None = None) -> dict:
    src = source_file or ctx.project.meta.source_file
    if not src:
        # maybe already ingested in a previous run
        if ctx.store.cleaned_text_path().exists():
            ctx.log.info("ingest: 已存在 cleaned.txt，跳过")
            return {"skipped": True}
        raise ValueError("没有指定输入小说/剧本文件")

    raw = read_source(src)
    text = clean(raw)
    chapters = split_chapters(text)

    ctx.store.cleaned_text_path().write_text(text, encoding="utf-8")
    ctx.store.chapters_path().write_text(
        json.dumps(chapters, ensure_ascii=False, indent=2), encoding="utf-8")

    ctx.project.meta.source_file = str(src)
    if not ctx.project.meta.title:
        ctx.project.meta.title = ctx.project.meta.name
    ctx.save()

    ctx.log.info("ingest: %d 字，检测到 %d 个章节块", len(text), len(chapters))
    return {"chars": len(text), "chapters": len(chapters)}
