"""Text utilities: cleaning, chapter detection and token-safe chunking."""
from __future__ import annotations

import re
from pathlib import Path

# 中文小说常见章节标题
_CHAPTER_RE = re.compile(
    r"^\s*(?:第[0-9零一二三四五六七八九十百千两]+[章节回卷集篇]|"
    r"chapter\s+\d+|序章|楔子|尾声|番外|后记)\s*[:：\.、]?\s*\S{0,30}",
    re.IGNORECASE | re.MULTILINE,
)

_SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?；;…])\s*")


def read_source(path: str | Path) -> str:
    """Read .txt/.md/.docx into plain text."""
    p = Path(path)
    if p.suffix.lower() in (".docx",):
        try:
            import docx2txt
            return docx2txt.process(str(p))
        except ImportError:
            raise RuntimeError("需要 docx2txt 才能读取 .docx：pip install dramakit[docx]")
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="ignore")


def clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\u3000", " ", text)               # 全角空格
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_chapters(text: str) -> list[dict]:
    """Return [{title, body}] using chapter headings; falls back to one block."""
    matches = list(_CHAPTER_RE.finditer(text))
    chapters: list[dict] = []
    if not matches:
        return [{"title": "", "body": text}]
    # leading preamble before first heading
    if matches[0].start() > 40:
        pre = text[: matches[0].start()].strip()
        if pre:
            chapters.append({"title": "开篇", "body": pre})
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            chapters.append({"title": m.group(0).strip(), "body": body})
    return chapters


def split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENT_SPLIT_RE.split(text) if s.strip()]
    return parts


def estimate_reading_seconds(text: str, cps: float = 4.2) -> float:
    """Rough spoken duration. Chinese ~4.2 chars/sec at normal pace."""
    n = len(re.sub(r"\s", "", text))
    return round(n / cps, 2)


def chunk_by_chars(text: str, max_chars: int, overlap: int = 0) -> list[str]:
    """Split long text into <=max_chars blocks, preferring paragraph/sentence
    boundaries, with optional overlap for context continuity."""
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]
    blocks: list[str] = []
    buf = ""
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(buf) + len(para) + 1 <= max_chars:
            buf = f"{buf}\n\n{para}" if buf else para
            continue
        if buf:
            blocks.append(buf)
            buf = buf[-overlap:] if overlap else ""
        # para itself too big -> split by sentences
        if len(para) > max_chars:
            cur = ""
            for s in split_sentences(para):
                if len(cur) + len(s) <= max_chars:
                    cur += s
                else:
                    if cur:
                        blocks.append(cur)
                    cur = s
            buf = cur
        else:
            buf = para
    if buf:
        blocks.append(buf)
    return [b for b in blocks if b.strip()]
