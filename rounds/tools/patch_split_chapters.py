"""A chapter is a chapter, and an episode is part of one.

When there are fewer chapters than episodes, each chapter is divided
into as many episodes as it needs and cut at a paragraph - so a scene
is never cut in half, and the story of a chapter stays in its own
episodes.  Before, the text was cut by character count and an episode
could start in the middle of a scene, with the rest of it in the next
episode.
"""
import pathlib

P = pathlib.Path(r"E:\dramakit\dramakit\pipeline\segment.py")
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

old = '''def _split_blocks_with_chapters(text: str, chapters: list[dict], n: int,
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
            body = "\\n\\n".join(c["body"] for c in part)
            if body.strip():
                blocks.append((body, [c.get("index", 0) for c in part]))
        if blocks:
            return blocks'''

new = '''def _split_chapter(body: str, parts: int) -> list[str]:
    """A chapter cut into pieces, at the paragraphs.

    A scene is never cut in half: the pieces are whole paragraphs, and
    the piece that would be too small is given to its neighbour.
    """
    if parts <= 1:
        return [body]
    paras = [p for p in body.split("\\n\\n") if p.strip()]
    if not paras:
        return [body]
    # the pieces are as even as the paragraphs allow
    per = len(paras) / parts
    out: list[str] = []
    cur: list[str] = []
    for i, p in enumerate(paras):
        cur.append(p)
        want = min(parts, int(i / per) + 1)
        if len(cur) >= max(1, round(per)) and len(out) < parts - 1:
            out.append("\\n\\n".join(cur))
            cur = []
    if cur:
        out.append("\\n\\n".join(cur))
    # the pieces that came out empty are folded into the one before
    return [o for o in out if o.strip()] or [body]


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
            body = "\\n\\n".join(c["body"] for c in part)
            if body.strip():
                blocks.append((body, [c.get("index", 0) for c in part]))
        if blocks:
            return blocks
    if cfg.respect_chapters and chapters:
        # fewer chapters than episodes: every chapter is divided into as
        # many episodes as it needs, and the pieces are whole
        # paragraphs - so a scene is never cut in half
        total = sum(len(c.get("body", "")) for c in chapters) or 1
        blocks = []
        left = n
        for i, c in enumerate(chapters):
            body = c.get("body", "")
            share = len(body) / total
            parts = int(round(share * n))
            if i == len(chapters) - 1:
                parts = left
            parts = max(1, min(parts, left))
            for piece in _split_chapter(body, parts):
                if piece.strip():
                    blocks.append((piece, [c.get("index", 0)]))
            left -= parts
            if left <= 0:
                break
        if blocks:
            return blocks'''

assert old in text
text = text.replace(old, new, 1)

if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("切集改成一集不跨章了")
