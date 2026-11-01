"""An instruction can name chapters, and a cut remembers what it cut.

The command box could only say episodes, so "前十章" had nowhere to land:
the parser has no chapters field, and segment - the one stage that decides
which chapters become episodes - reads only meta.chosen_chapters, which
nobody had set. It cut the whole book, and the ten the user wanted were
buried in a hundred and fifty.

Chapters are now a parameter of run_pipeline: the parser can emit them,
the run writes them into chosen_chapters, and segment cuts only those.
The plan shown before anything runs names the chapters as well, so a
misreading is visible before it costs anything.

A cut also records what it cut even when it took the whole book. Without
that, segmented_chapters stayed empty, a second run could not tell what
had been made, and "resume" had nothing to resume from.

Every anchor here is ASCII on purpose: the file's Chinese is fine, but
matching on it has already failed once and there is no reason to depend
on it.
"""
import re
from pathlib import Path

a = Path(r"E:\\dramakit\\dramakit\\ai\\actions.py")
t = a.read_text(encoding="utf-8")

# ------------------------------------------- 1. chapters is a parameter --
old_params = '        "params": ["project", "episodes", "stages", "overrides"],'
new_params = ('        # chapters are the input, episodes the output: naming\n'
              '        # chapters is how a run is told to make part of a book\n'
              '        "params": ["project", "chapters", "episodes", "stages", "overrides"],')
assert t.count(old_params) == 1, f"params 锚点出现 {t.count(old_params)} 次"
t = t.replace(old_params, new_params, 1)

# --------------------------------------------- 2. normalise the ranges --
old_norm = '''    if "episodes" in allowed:
        eps = raw.get("episodes") or []'''
new_norm = '''    if "chapters" in allowed:
        raw_ch = raw.get("chapters") or []
        if isinstance(raw_ch, (int, str)):
            raw_ch = [raw_ch]
        # an instruction says "1-10" far more often than it lists ten
        # numbers, so a range is expanded here rather than left to the
        # model to enumerate
        expanded: list[int] = []
        for c in raw_ch:
            piece = str(c).strip()
            if "-" in piece:
                lo, _, hi = piece.partition("-")
                if lo.strip().isdigit() and hi.strip().isdigit():
                    lo_n, hi_n = int(lo), int(hi)
                    expanded.extend(range(min(lo_n, hi_n), max(lo_n, hi_n) + 1))
                    continue
            if piece.isdigit():
                expanded.append(int(piece))
        params["chapters"] = sorted(set(expanded))
    if "episodes" in allowed:
        eps = raw.get("episodes") or []'''
assert t.count(old_norm) == 1, "episodes 归一化锚点没找到"
t = t.replace(old_norm, new_norm, 1)

# --------------------------------- 3. the run writes them into the book --
old_write = '''    if p.get("episodes"):
        cfg.pipeline.only_episodes = p["episodes"]'''
new_write = '''    # the chapters this run is made from. segment reads this and cuts
    # nothing else, so it is the only thing that limits a partial book
    if p.get("chapters"):
        proj = store.load()
        proj.meta.chosen_chapters = sorted({int(c) for c in p["chapters"]})
        store.save(proj)
    if p.get("episodes"):
        cfg.pipeline.only_episodes = p["episodes"]'''
assert t.count(old_write) == 1, "_do_run 的 episodes 锚点没找到"
t = t.replace(old_write, new_write, 1)

# --------------------------------- 4. the plan shown names the chapters --
# the summary line builds a string about episodes; add one about chapters
# ahead of it, so a plan that misread "前十章" is visible before it runs
m = re.search(r'\n(\s*)eps = f"[^\n]*?if p\.get\("episodes"\) else "[^\n]*?"\n', t)
assert m, "摘要文案锚点没找到"
indent = m.group(1)
added = ('\n' + indent
         + 'chs = (f"{min(p[\'chapters\'])}-{max(p[\'chapters\'])} '
         + '(of {len(p[\'chapters\'])})" if p.get("chapters") else "all chapters")')
t = t[:m.start()] + added + m.group(0) + t[m.end():]

# ------------------------------------------ 5. the parser is told about --
old_fmt = '        "\\"episodes\\": ['
new_fmt = '        "\\"chapters\\": [chapter numbers or a range like 1-10], "\n        "\\"episodes\\": ['
if old_fmt in t:
    t = t.replace(old_fmt, new_fmt, 1)
    print("  提示词：输出格式加了 chapters")
else:
    print("  提示词：输出格式锚点没找到（跳过）")

a.write_text(t, encoding="utf-8")
print("actions.py: 指令能说「章」了")

# ------------------- 6. a whole-book cut records what it cut -------------
seg = Path(r"E:\\dramakit\\dramakit\\pipeline\\segment.py")
sv = seg.read_text(encoding="utf-8")

old_rec = '''    # remember which chapters are now episodes, and which season they made
    if todo:'''
new_rec = '''    # Remember which chapters are now episodes, and which season they made.
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
    if todo:'''
if old_rec in sv and "整本书切分，记录" not in sv:
    sv = sv.replace(old_rec, new_rec, 1)
    seg.write_text(sv, encoding="utf-8")
    print("segment.py: 整本书切分也记录 segmented_chapters")
else:
    print("segment.py: 跳过")
