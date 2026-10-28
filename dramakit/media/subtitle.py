"""Subtitle generation: SRT (soft/portable) and ASS (styled, for burning).

红果短剧 convention: large bold bottom-center dialogue, a colored speaker label
before the line, strong black outline for legibility over bright footage.
"""
from __future__ import annotations

from pathlib import Path

from ..models import LineKind, SubtitleCue


def _srt_time(t: float) -> str:
    """HH:MM:SS,mmm.

    The rounding is done on the whole timestamp: rounding the fraction on its
    own can produce 100 centiseconds, and dropping that carry moves a cue a
    whole second early.
    """
    if t < 0:
        t = 0.0
    total_ms = int(round(t * 1000))
    ms = total_ms % 1000
    s = (total_ms // 1000) % 60
    m = (total_ms // 60000) % 60
    h = total_ms // 3600000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ass_time(t: float) -> str:
    """H:MM:SS.cc for the ASS format."""
    if t < 0:
        t = 0.0
    total_cs = int(round(t * 100))
    cs = total_cs % 100
    s = (total_cs // 100) % 60
    m = (total_cs // 6000) % 60
    h = total_cs // 360000
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(text: str) -> str:
    return (text or "").replace("\r", " ").replace("\n", " ").strip()


def write_srt(cues: list[SubtitleCue], out_path: str | Path) -> str:
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for i, c in enumerate(cues, 1):
        speaker = f"{c.speaker}：" if c.speaker and c.speaker not in ("旁白", "解说") else ""
        lines.append(str(i))
        lines.append(f"{_srt_time(c.start)} --> {_srt_time(c.end)}")
        lines.append(f"{speaker}{_clean(c.text)}")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)


def _text_width(text: str) -> float:
    """How wide a line is, in characters: a Chinese one is a full width."""
    total = 0.0
    for ch in text or "":
        total += 1.0 if ord(ch) > 0x2E80 else 0.55
    return total


def _ass_header(style: dict, width: int, height: int,
                longest: float = 0.0) -> str:
    font = style.get("font", "Microsoft YaHei")
    size = style.get("font_size", 16)
    primary = style.get("primary_color", "&H00FFFFFF")
    outline_c = style.get("outline_color", "&H00000000")
    outline = style.get("outline", 2)
    shadow = style.get("shadow", 0)
    margin_v = style.get("margin_v", 220)
    bold = -1 if style.get("bold", True) else 0
    align = style.get("alignment", 2)
    # narration cards: own slot at the top so they never sit on the dialogue
    narr_font = style.get("narration_font", font)
    narr_size = style.get("narration_font_size", 14)
    narr_color = style.get("narration_color", "&H00A0DCFA")
    narr_back = style.get("narration_back_color", "&H66000000")
    narr_margin = style.get("narration_margin_v", 40)
    # The font size is relative to a 288 high canvas. The margin is counted in
    # text heights above the bottom of the picture, so the subtitle sits just
    # above the edge whatever the frame is - a margin written in pixels for
    # another frame lands across the actors' faces.
    # The size follows the width of the picture: a line has to fit
    # sideways, and in a tall frame a size taken from the height runs off
    # both edges.
    k = width / 960.0
    scaled = int(round(size * k))
    if longest > 0:
        room = (width - 2 * int(round(60 * height / 1080))) / longest
        scaled = max(12, min(scaled, int(room * 0.95)))
    narr_scaled = int(round(narr_size * k))
    heights = float(margin_v or 1)
    margin_v = int(round(scaled * heights))
    # a share of the height: in a tall frame the bottom is where the
    # platform's own buttons sit, so the subtitle has to clear them
    pct = float(style.get("margin_v_pct") or 0)
    if pct > 0:
        margin_v = max(margin_v, int(round(height * pct / 100.0)))
    narr_margin = int(round(narr_scaled * 0.8))
    # A caption card belongs in the middle of the picture: at the top it
    # reads like a note the editor left in the frame.
    narr_align = style.get("narration_alignment", 5)
    margin_h = int(round(60 * height / 1080))
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{scaled},{primary},&H00FFFFFF,{outline_c},&H64000000,{bold},0,0,0,100,100,0,0,1,{outline},{shadow},{align},{margin_h},{margin_h},{margin_v},1
Style: Speaker,{font},{int(scaled*0.72)},{style.get("speaker_color","&H0000E5FF")},&H00FFFFFF,{outline_c},&H64000000,{bold},0,0,0,100,100,0,0,1,{outline},0,{align},{margin_h},{margin_h},{margin_v + int(scaled*1.25)},1
Style: Narration,{narr_font},{narr_scaled},{narr_color},&H00FFFFFF,{outline_c},{narr_back},{bold},1,0,0,100,100,0,0,3,1,0,{narr_align},{margin_h},{margin_h},{narr_margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(cues: list[SubtitleCue], out_path: str | Path, *, style: dict,
              width: int = 1080, height: int = 1920, show_speaker: bool = True) -> str:
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    longest = 0.0
    for c in cues:
        if c.kind in (LineKind.NARRATION, LineKind.CAPTION):
            continue
        longest = max(longest, _text_width(_clean(c.text)))
    parts = [_ass_header(style, width, height, longest)]
    for c in cues:
        start, end = _ass_time(c.start), _ass_time(c.end)
        text = _clean(c.text).replace(":", "：")
        if c.kind in (LineKind.NARRATION, LineKind.CAPTION):
            # narration card: own style, no speaker label
            parts.append(f"Dialogue: 0,{start},{end},Narration,,0,0,0,,{text}")
            continue
        named = c.speaker and c.speaker not in ("旁白", "解说")
        if show_speaker and named:
            parts.append(f"Dialogue: 0,{start},{end},Speaker,,0,0,0,,{c.speaker}")
        parts.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return str(out_path)
