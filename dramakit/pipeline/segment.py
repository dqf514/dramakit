"""Stage 3 — segment: cut the chosen chapters into episodes.

Episode count is not a question for the user.  It comes from the text:
how long the picked chapters take to read, divided by the target episode
length, snapped to chapter boundaries where the chapters are big enough.
A 3-minute chapter is one episode; a 30-minute chapter is six.

A project is made one season at a time, so segment works on one season's
chapters and appends to the episodes that already exist.  The chapters
already cut are remembered in meta.segmented_chapters, and a run only
turns the remaining picked chapters into episodes - numbered after the
ones that already exist, leaving their scenes, shots, prompts and
rendered media exactly as they were.  Picking chapter 7 after chapters
1-6 gives you episode 8, not a new episode 1.

Each new episode is stamped with the season it was made in, so that a
rerun of season 3 never rewrites season 1's episodes.
"""
from __future__ import annotations

import json

from ..models import Episode, Status
from ..prompts import templates as T
from ..utils.text import chunk_by_chars, estimate_reading_seconds
from .base import Context

CHARS_PER_SEC = 4.2


def _episode_count(total_chars: float, cfg, n_chapters: int) -> int:
    if cfg.strategy == "fixed_count" and cfg.episode_count > 0:
        return cfg.episode_count
    if cfg.strategy == "by_chapter" and n_chapters > 0:
        return max(1, n_chapters)
    total_sec = total_chars / CHARS_PER_SEC
    n = max(1, round(total_sec / max(cfg.episode_duration, 10)))
    return max(1, min(n, 500))


def _split_blocks(text: str, chapters: list[dict], n: int, cfg) -> list[str]:
    return [body for body, _ in _split_blocks_with_chapters(text, chapters, n, cfg)]


def _split_blocks_with_chapters(text: str, chapters: list[dict], n: int,
                                cfg) -> list[tuple[str, list[int]]]:
    """The blocks of text, and the chapters each block was made of.

    The chapters are the ones that were picked; each carries its index.
    A block is either a run of whole chapters (when the chapters are
    big enough to fill an episode) or a slice of the joined text, and
    a slice is found by what is in it rather than by where it starts,
    because the text is cut at paragraph boundaries and the paragraphs
    are stripped on the way.
    """
    if cfg.respect_chapters and chapters and len(chapters) >= n:
        per = len(chapters) / n
        blocks: list[tuple[str, list[int]]] = []
        for i in range(n):
            lo = int(round(i * per))
            hi = int(round((i + 1) * per))
            hi = max(hi, lo + 1)
            part = chapters[lo:hi]
            body = "\n\n".join(c["body"] for c in part)
            if body.strip():
                blocks.append((body, [c.get("index", 0) for c in part]))
        if blocks:
            return blocks
    target = max(200, int(len(text) / max(n, 1)))
    if cfg.max_chars_per_episode > 0:
        target = cfg.max_chars_per_episode
    out: list[tuple[str, list[int]]] = []
    for chunk in chunk_by_chars(text, target):
        flat = " ".join(chunk.split())
        idxs: list[int] = []
        for c in chapters:
            body = (c.get("body") or "").strip()
            if not body:
                continue
            key = " ".join(body[:40].split())
            if key and key in flat:
                idxs.append(c.get("index", 0))
        out.append((chunk, idxs))
    return out


def _chapters_to_cut(ctx: Context) -> list:
    """The picked chapters that have not been cut into episodes yet.

    Picking chapters appends to chosen; running segment consumes them.  If
    nothing has been picked, the whole book is the input - the old path,
    for projects made before chapter picking existed.
    """
    meta = ctx.project.meta
    chosen = list(meta.chosen_chapters or [])
    done = set(meta.segmented_chapters or [])
    chapters_meta = list(meta.chapters or [])
    if not chosen or not chapters_meta:
        return []
    return [c for c in chapters_meta if c.index in chosen and c.index not in done]


def _read_chapter(ctx: Context, c) -> str:
    f = (ctx.store.root / c.file) if c.file else None
    return f.read_text(encoding="utf-8") if f and f.exists() else ""


def run(ctx: Context) -> dict:
    cfg = ctx.cfg.segment
    todo = _chapters_to_cut(ctx)
    meta = ctx.project.meta
    # The season this batch belongs to is settled before the episodes are
    # made. An episode records the season it belongs to, and a run that
    # has just created that season would otherwise tag them with the
    # season it had before - which is none. Every stage after this one
    # looks for the episodes in the season they were made in, and would
    # find nothing there.
    if todo:
        ctx.seed_season([c.index for c in todo])
    season_idx = ctx.season_index

    # nothing new to cut, and the project already has episodes: done.
    if not todo and ctx.project.episodes:
        ctx.log.info("segment: 没有新章节要切，已有 %d 集", len(ctx.project.episodes))
        return {"skipped": True, "episodes": len(ctx.project.episodes)}

    if todo:
        parts = [_read_chapter(ctx, c) for c in todo]
        blocks_src = [{"body": b, "index": c.index}
                      for b, c in zip(parts, todo) if b.strip()]
        text = "\n\n".join(b["body"] for b in blocks_src)
        ctx.log.info("segment: 第%d季 新切 %d 个章节（%d 字），已有 %d 集",
                     season_idx, len(blocks_src), len(text), len(ctx.project.episodes))
    else:
        text = ctx.store.cleaned_text_path().read_text(encoding="utf-8")
        blocks_src = []
        chapters_json = ctx.store.chapters_path()
        if chapters_json.exists():
            raw = json.loads(chapters_json.read_text(encoding="utf-8"))
            blocks_src = [{"body": c.get("body", ""), "index": i}
                          for i, c in enumerate(raw, 1)]
        ctx.log.info("segment: 未选章节，用整本书（%d 字）", len(text))

    n = _episode_count(len(text), cfg, len(blocks_src))
    if blocks_src and len(blocks_src) >= n:
        chapters_for_split = [{"body": b["body"], "index": b.get("index", 0)}
                              for b in blocks_src]
        new_blocks = _split_blocks_with_chapters(text, chapters_for_split, n, cfg)
    else:
        new_blocks = _split_blocks_with_chapters(text, blocks_src, n, cfg)

    # number after what already exists, so a second batch appends
    first_index = (max((e.index for e in ctx.project.episodes), default=0) + 1)
    total_new = len(new_blocks)
    ctx.log.info("segment: 切成 %d 集（策略=%s），从第 %d 集起",
                 total_new, cfg.strategy, first_index)

    llm = ctx.providers.llm_for("segment")
    episodes: list[Episode] = list(ctx.project.episodes)
    for j, (block, chapter_indexes) in enumerate(new_blocks):
        idx = first_index + j
        ctx.store.episode_source_path(idx).write_text(block, encoding="utf-8")
        ep = Episode(
            id=f"ep{idx:03d}", index=idx, season=season_idx,
            duration_target=cfg.episode_duration,
            source_path=ctx.store.rel(ctx.store.episode_source_path(idx)),
            chapter_indexes=list(chapter_indexes),
        )
        try:
            dur = estimate_reading_seconds(block, CHARS_PER_SEC)
            extra = "本集为开场，需冷开场直接抛冲突。" if (idx == 1 and cfg.cold_open) else ""
            user = T.render(T.SEGMENT_USER, title=ctx.project.meta.title or "本剧",
                            ep_index=idx, ep_total=first_index - 1 + total_new,
                            duration=int(dur), hook_style=cfg.hook_style,
                            extra_hint=extra, text=block[:6000])
            data = llm.complete_json(T.SEGMENT_SYSTEM, user)
            if isinstance(data, list):
                data = data[0] if data else {}
            ep.title = data.get("title") or f"第{idx}集"
            ep.logline = data.get("logline", "")
            ep.hook = data.get("hook", "")
            ep.recap = data.get("recap", "") if cfg.opening_recap else ""
            ep.key_beats = data.get("key_beats", []) or []
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("segment: 第%d集打包失败(%s)，用占位标题", idx, e)
            ep.title = f"第{idx}集"
        ep.duration_target = round(estimate_reading_seconds(block, CHARS_PER_SEC), 1) \
            or cfg.episode_duration
        episodes.append(ep)

    ctx.project.episodes = episodes

    # Remember which chapters are now episodes, and which season they made.
    # The whole-book path records it too: without this a second run cannot
    # tell what was already made, and there is nothing to resume from -
    # which is how the same book gets cut twice.
    if not todo and blocks_src:
        cut = sorted({b["index"] for b in blocks_src if b.get("index")})
        if cut:
            done = set(meta.segmented_chapters or [])
            done.update(cut)
            meta.segmented_chapters = sorted(done)
            ctx.log.info("segment: 整本书切分，记录 %d 章", len(cut))

    # remember which chapters are now episodes, and which season they made
    if todo:
        already = set(meta.segmented_chapters or [])
        already.update(c.index for c in todo)
        meta.segmented_chapters = sorted(already)
        # the season owns the chapters it was made from - it was settled
        # before the episodes were made, so this only records them
        season = ctx.season or ctx.seed_season([c.index for c in todo])
        season.episode_range = [first_index, first_index + total_new - 1]
        ctx.mark_chapter_season([c.index for c in todo])
        # canon: what has been made, across all seasons
        ctx.project.canon.done_chapters = sorted(
            set(ctx.project.canon.done_chapters or []) | set(meta.segmented_chapters))
        ctx.log.info("segment: 第%d季 已记录切过的章节 %d 个",
                     season_idx, len(meta.segmented_chapters))

    ctx.project.stage_status["segment"] = "done"
    season = ctx.season
    if season is not None:
        season.stage_status["segment"] = "done"
    ctx.save()
    return {"episodes": len(episodes), "new": total_new, "season": season_idx}
