"""If the model's pattern finds no chapters, try the headings books really use.

The model reads the head of the book and answers with a regex. It guesses
「第X章」because that is the common case, and a book that numbers its
chapters 第X回 or 第X节 then comes back with no chapters at all - the
pattern compiles, matches nothing, and the whole book is treated as one
block. The user sees a project with no table of contents and no way to
know why.

So the model's answer is a candidate, not a verdict. If it finds nothing,
the common Chinese and English heading styles are tried, and the one that
finds the most chapters wins - a book's own headings decide how it is cut,
not the model's first guess.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\catalog.py")
s = p.read_text(encoding="utf-8", errors="replace")

if "_COMMON_HEADING_PATTERNS" in s:
    print("catalog.py: 已有标题兜底，跳过")
    raise SystemExit(0)

# the patterns a Chinese novel actually uses for its chapter headings
marker = "# Chinese and English novels number their chapters in more than\n" \
         "# one way; the model guesses the common one and misses the rest.\n" \
         "_COMMON_HEADING_PATTERNS = [\n" \
         "    r\"^第[0-9一二三四五六七八九十百千]+章.*$\",\n" \
         "    r\"^第[0-9一二三四五六七八九十百千]+回.*$\",\n" \
         "    r\"^第[0-9一二三四五六七八九十百千]+节.*$\",\n" \
         "    r\"^卷[〇零一二三四五六七八九十百千0-9]+.*$\",\n" \
         "    r\"^Chapter\\s+\\d+.*$\",\n" \
         "    r\"^\\d{1,4}[.、．]\\s*\\S.*$\",\n" \
         "]\n\n\n"

anchor = "def _heading_pattern(text: str, ctx: Context)"
assert anchor in s, "找不到 _heading_pattern"
s = s.replace(anchor, marker + anchor, 1)

# the fallback itself, called where the pattern is decided
old_ret = "    return chapter_pat, ([volume_pat] if volume_pat else [])"
new_ret = '''    # The model's pattern is a candidate. If it finds nothing, the book is
    # about to be treated as one undivided block, so the common heading
    # styles get a turn and the most productive one wins.
    def _hits(pat: str) -> int:
        try:
            return len(re.findall(re.compile(pat), text, re.M))
        except re.error:
            return 0

    if _hits(chapter_pat) < 2:
        best, best_n = chapter_pat, _hits(chapter_pat)
        for cand in _COMMON_HEADING_PATTERNS:
            n = _hits(cand)
            if n > best_n:
                best, best_n = cand, n
        if best_n >= 2:
            ctx.log.info("catalog: 模型给的正则只找到 %d 章，改用 %s（%d 章）",
                         _hits(chapter_pat), best, best_n)
            chapter_pat = best
    return chapter_pat, ([volume_pat] if volume_pat else [])'''
assert old_ret in s, "找不到 _heading_pattern 的返回语句"
s = s.replace(old_ret, new_ret, 1)

p.write_text(s, encoding="utf-8")
print("catalog.py: 模型的正则找不到章节时，试常见标题样式取命中最多的")
