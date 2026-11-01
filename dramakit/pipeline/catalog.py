"""The novel, cut into volumes and chapters, before anything is written.

A novel can be a million characters.  Handing it to a model in one piece
is a way to spend the whole context on the parts that are not this
episode.  So the text is cut first:

  * the first stretch of the book tells the model how the book is
    organised - what marks a volume, what marks a chapter, what the
    headings look like - and the model answers with the pattern;
  * the book is then split by that pattern, volumes first and chapters
    inside them;
  * every chapter is written out on its own, into `source/volumes/`, so
    the console can show the table of contents and the director can work
    one chapter at a time.

The chapters are the project's own assets: they are listed on the project,
readable in the console, and the episodes are cut from the ones the user
picks.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..utils.text import clean, read_source
from .base import Context

# how much of the book the model reads to learn how it is organised
HEAD_CHARS = 10000


def volumes_dir(ctx: Context) -> Path:
    d = ctx.store.root / "source" / "volumes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _heading_pattern(text: str, ctx: Context) -> tuple[str, list[str]]:
    """What marks a chapter and a volume in this book.

    The model is shown the head of the book and asked for the pattern; a
    regex it can answer with, and a short note on what it found.
    """
    head = text[:HEAD_CHARS]
    llm = ctx.providers.llm_for("analyze")
    data = llm.complete_json(
        "你是书籍分卷分章的专家。只输出JSON。",
        "下面是小说的开头。请判断这本书用什么标记分章、什么标记分卷。\n"
        "注意：有些书用「第X章」「第X节」「Chapter X」，有些用空行+标题，"
        "有些整本没有分章只有段落。\n"
        "输出JSON：\n"
        "{\"chapter_pattern\": \"python正则表达式，匹配一个章节标题行，"
        "用 ^ 开头、$ 结尾，比如 ^第[0-9一二三四五六七八九十百千]+章\", "
        "\"volume_pattern\": \"python正则，匹配分卷标题，没有分卷就给空字符串\", "
        "\"found\": \"你在这本书里看到的标题样式，举3个例子\"}\n\n"
        "开头：\n\"\"\"\n" + head + "\n\"\"\"")
    if isinstance(data, list):
        data = data[0] if data else {}
    chapter_pat = (data.get("chapter_pattern") or "^第[0-9一二三四五六七八九十百千]+章").strip()
    volume_pat = (data.get("volume_pattern") or "").strip()
    found = str(data.get("found") or "")[:200]
    # the pattern has to compile, or the whole cut is worthless
    for name, pat in (("chapter", chapter_pat), ("volume", volume_pat)):
        if not pat:
            continue
        try:
            re.compile(pat)
        except re.error as e:
            ctx.log.warning("catalog: %s 的正则不能用（%s），改用兜底", name, e)
            if name == "chapter":
                chapter_pat = "^第[0-9一二三四五六七八九十百千]+章"
            else:
                volume_pat = ""
    ctx.log.info("catalog: 章标题 %s | 卷标题 %s | 看到的样式：%s",
                 chapter_pat, volume_pat or "（无分卷）", found)
    return chapter_pat, ([volume_pat] if volume_pat else [])


def _split(text: str, chapter_pat: str, volume_pat: str) -> list[dict]:
    """The book, cut into volumes and chapters: [{volume, index, title, body}]."""
    lines = text.splitlines()
    vol_re = re.compile(volume_pat) if volume_pat else None
    ch_re = re.compile(chapter_pat) if chapter_pat else None

    cuts: list[tuple[str, int, str]] = []   # (volume, line, title)
    vol = ""
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if vol_re and vol_re.search(s):
            vol = s[:60]
            continue
        if ch_re and ch_re.search(s):
            cuts.append((vol, i, s[:80]))
    if not cuts:
        # no chapters the pattern could find: the book is one chapter
        return [{"volume": "", "index": 1, "title": "正文",
                 "body": text.strip()}]
    out = []
    for n, (v, i, title) in enumerate(cuts):
        end = cuts[n + 1][1] if n + 1 < len(cuts) else len(lines)
        body = "\n".join(lines[i:end]).strip()
        if len(body) < 200:
            continue
        out.append({"volume": v, "index": len(out) + 1, "title": title,
                    "body": body})
    return out


def run(ctx: Context, source_file: str | None = None) -> dict:
    src = source_file or ctx.project.meta.source_file
    if not src:
        raise ValueError("没有指定输入小说/剧本文件")
    text = clean(read_source(src))
    chapter_pat, vols = _heading_pattern(text, ctx)
    vpat = vols[0] if vols else ""
    chapters = _split(text, chapter_pat, vpat)

    # every chapter on its own, in the folder the console shows
    vdir = volumes_dir(ctx)
    for old in vdir.glob("*.txt"):
        old.unlink()
    for c in chapters:
        name = f"vol{c['volume'] or 'x'}_ch{c['index']:03d}.txt"
        (vdir / name).write_text(c["body"], encoding="utf-8")
        c["file"] = str(Path("source") / "volumes" / name)

    # and the table of contents on the project
    ctx.project.meta.volumes = sorted({c["volume"] for c in chapters})
    ctx.project.meta.chapters = [
        {"volume": c["volume"], "index": c["index"], "title": c["title"],
         "chars": len(c["body"]), "file": c["file"]} for c in chapters]
    ctx.project.meta.chapter_pattern = chapter_pat
    ctx.project.meta.volume_pattern = vpat
    ctx.save()

    # the whole book still goes to the cleaned file, for reference
    ctx.store.cleaned_text_path().write_text(text, encoding="utf-8")
    ctx.log.info("catalog: %d 字 → %d 卷 %d 章", len(text),
                 len(set(c["volume"] for c in chapters)), len(chapters))
    return {"chars": len(text), "volumes": len(set(c["volume"] for c in chapters)),
            "chapters": len(chapters)}
