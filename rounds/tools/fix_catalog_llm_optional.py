"""Cutting chapters is regex work; the model is a convenience, not a gate.

_heading_pattern asks the model what marks a chapter in this book, then
falls over when the model cannot be reached - so a book with plainly
numbered chapters comes back with no table of contents at all, because a
regex question was made to depend on a network service.

The model is worth asking: it handles headings nobody anticipated. But its
answer is one candidate among several. When it is unreachable, or when its
pattern finds nothing, the common Chinese and English heading styles are
tried and the one that finds the most chapters wins. A book's own
headings decide how it is cut.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\catalog.py")
s = p.read_text(encoding="utf-8", errors="replace")

start = s.index("def _heading_pattern(")
end = s.index("\ndef ", start + 10)

new_fn = '''def _heading_pattern(text: str, ctx: Context) -> tuple[str, list[str]]:
    """What marks a chapter and a volume in this book.

    The model is shown the head of the book and asked for the pattern; a
    regex it can answer with, and a short note on what it found. That is
    the best answer available, and the only one that sees a heading style
    nobody thought to list - so it is asked first.

    It is not the only answer, and it is not required. A model that is
    offline, or one that guesses 第X章 for a book that numbers its chapters
    第X回, leaves the book with no chapters at all if its word is final.
    So it is one candidate: what it returns, and what the common heading
    styles return, are measured against the text and the most productive
    wins. Cutting a book into chapters is regex work that happens to
    benefit from a model, not the other way round.
    """

    def _hits(pat: str) -> int:
        try:
            return len(re.findall(re.compile(pat), text, re.M))
        except re.error:
            return 0

    def _best(cands: list[str], floor: int = 2) -> tuple[str, int]:
        """The candidate that finds the most chapters, and how many."""
        best, n = "", 0
        for c in cands:
            if not c:
                continue
            got = _hits(c)
            if got > n:
                best, n = c, got
        return (best, n) if n >= floor else ("", 0)

    chapter_pat = ""
    volume_pat = ""
    found = ""
    try:
        head = text[:HEAD_CHARS]
        llm = ctx.providers.llm_for("analyze")
        data = llm.complete_json(
            "你是书籍分卷分章的专家。只输出JSON。",
            "下面是小说的开头。请判断这本书用什么标记分章、什么标记分卷。\\n"
            "注意：有些书用「第X章」「第X节」「第X回」「Chapter X」，有些用空行+标题，"
            "有些整本没有分章只有段落。\\n"
            "输出JSON：\\n"
            "{\\"chapter_pattern\\": \\"python正则表达式，匹配一个章节标题行，"
            "用 ^ 开头、$ 结尾，比如 ^第[0-9一二三四五六七八九十百千]+章\\", "
            "\\"volume_pattern\\": \\"python正则，匹配分卷标题，没有分卷就给空字符串\\", "
            "\\"found\\": \\"你在这本书里看到的标题样式，举3个例子\\"}\\n\\n"
            "开头：\\n\\"\\"\\"\\n" + head + "\\n\\"\\"\\"")
        if isinstance(data, list):
            data = data[0] if data else {}
        chapter_pat = (data.get("chapter_pattern") or "").strip()
        volume_pat = (data.get("volume_pattern") or "").strip()
        found = str(data.get("found") or "")[:200]
        # the pattern has to compile, or the cut is worthless
        for name, pat in (("chapter", chapter_pat), ("volume", volume_pat)):
            if not pat:
                continue
            try:
                re.compile(pat)
            except re.error as e:
                ctx.log.warning("catalog: %s 的正则不能用（%s），改用兜底", name, e)
                if name == "chapter":
                    chapter_pat = ""
                else:
                    volume_pat = ""
    except Exception as e:  # noqa: BLE001
        # A model that is not there is not a reason to give up on the book:
        # the headings below are the ordinary cases and they need no model.
        ctx.log.warning("catalog: 问模型分章样式失败（%s），改用常见标题样式", str(e)[:120])

    # The model's answer is a candidate. If it finds nothing, the book would
    # become one undivided block, so the common heading styles get a turn.
    if _hits(chapter_pat) < 2:
        best, n = _best(_COMMON_HEADING_PATTERNS)
        if best and (not chapter_pat or n > _hits(chapter_pat)):
            ctx.log.info("catalog: 改用常见标题样式 %s（%d 章）", best, n)
            chapter_pat = best

    if not chapter_pat:
        # nothing matched anywhere: the book is one chapter, and that is a
        # real answer rather than an error
        chapter_pat = _COMMON_HEADING_PATTERNS[0]
        ctx.log.info("catalog: 没认出章节标题，整本书作为一章")

    ctx.log.info("catalog: 章标题 %s | 卷标题 %s | 看到的样式：%s",
                 chapter_pat, volume_pat or "（无分卷）", found or "（模型未答）")
    return chapter_pat, ([volume_pat] if volume_pat else [])


'''

s = s[:start] + new_fn + s[end + 1:]
p.write_text(s, encoding="utf-8")
print("catalog.py: 分章不再依赖 LLM，模型只是一条候选")
