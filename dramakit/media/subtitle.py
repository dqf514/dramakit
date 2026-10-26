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


def _ass_header(style: dict, width: int, height: int) -> str:
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
    narr_align = style.get("narration_alignment", 8)
    # ASS font sizes are relative to script resolution; scale up for 1080-wide
    scaled = int(round(size * (height / 288)))
    narr_scaled = int(round(narr_size * (height / 288)))
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{scaled},{primary},&H00FFFFFF,{outline_c},&H64000000,{bold},0,0,0,100,100,0,0,1,{outline},{shadow},{align},60,60,{margin_v},1
Style: Speaker,{font},{int(scaled*0.72)},{style.get("speaker_color","&H0000E5FF")},&H00FFFFFF,{outline_c},&H64000000,{bold},0,0,0,100,100,0,0,1,{outline},0,{align},60,60,{margin_v + int(scaled*1.25)},1
Style: Narration,{narr_font},{narr_scaled},{narr_color},&H00FFFFFF,{outline_c},{narr_back},{bold},1,0,0,100,100,0,0,3,1,0,{narr_align},80,80,{narr_margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(cues: list[SubtitleCue], out_path: str | Path, *, style: dict,
              width: int = 1080, height: int = 1920, show_speaker: bool = True) -> str:
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    parts = [_ass_header(style, width, height)]
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
