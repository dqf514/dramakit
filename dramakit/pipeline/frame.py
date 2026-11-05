"""The frame a project is made in.

The shape of the picture is not a detail of one stage: the stills are made
in it, the clips are made in it, the film is put together in it and the
quality check measures the result against it.  A picture made in another
shape is cropped to fit, and the crop is what takes the faces off - so the
project says what shape it wants and this module makes every stage agree.

The size the project asks for is the delivery size.  The stills keep the
size the config asks for, in the same shape - the picture models are
happier with a smaller canvas, and the film upscales it anyway.
"""
from __future__ import annotations

import math

from ..ai import looks


def _ratio_value(aspect_ratio: str) -> float:
    """The width over the height of a ratio like "9:16"."""
    a = looks.aspect(aspect_ratio)
    return 9 / 16 if a["id"] == "9:16" else 16 / 9


def fit_area(area: int, aspect_ratio: str) -> tuple[int, int]:
    """The size with that area in that shape, on multiples of 16."""
    area = max(1, int(area or 0))
    ar = _ratio_value(aspect_ratio)
    if ar >= 1:
        h = math.sqrt(area / ar)
        w = h * ar
    else:
        w = math.sqrt(area * ar)
        h = w / ar
    w = max(256, int(round(w / 16.0)) * 16)
    h = max(256, int(round(h / 16.0)) * 16)
    return w, h


def project_frame(art, cfg=None) -> tuple[int, int]:
    """The delivery size of a project, in pixels.

    A project that names a size gets it.  A project that names only the
    ratio gets the size from the list that keeps the area the config
    already asked for - so a landscape setup becomes a vertical one
    without the resolution jumping.
    """
    w = int(getattr(art, "frame_width", 0) or 0)
    h = int(getattr(art, "frame_height", 0) or 0)
    if w > 0 and h > 0:
        return w, h
    ratio = getattr(art, "aspect_ratio", "") or looks.DEFAULT_ASPECT
    area = 0
    if cfg is not None:
        area = int(getattr(cfg.compose, "width", 0) or 0) * int(
            getattr(cfg.compose, "height", 0) or 0)
    if area > 0:
        # the size from the list whose area is nearest the config's, so a
        # project that was set up before the list existed still lands on a
        # size the tools know
        best = None
        for s in looks.aspect(ratio)["sizes"]:
            d = abs(s["w"] * s["h"] - area)
            if best is None or d < best[0]:
                best = (d, s["w"], s["h"])
        if best:
            return best[1], best[2]
    return looks.size_for(ratio)


def apply_frame(cfg, art):
    """A copy of the settings that makes everything in the project's frame.

    The copy matters: the settings are the ones the whole console reads,
    and a project asking for a vertical frame must not turn the next
    project on the same machine into a vertical one.
    """
    c = cfg.model_copy(deep=True)
    w, h = project_frame(art, c)
    c.compose.width, c.compose.height = w, h
    c.comfyui.video_width, c.comfyui.video_height = w, h
    # the stills keep the size the config asks for, in the frame's shape
    sw = int(getattr(c.comfyui, "width", 0) or 0)
    sh = int(getattr(c.comfyui, "height", 0) or 0)
    if sw > 0 and sh > 0:
        sw, sh = fit_area(sw * sh, getattr(art, "aspect_ratio", "")
                          or looks.DEFAULT_ASPECT)
    else:
        sw, sh = w, h
    c.comfyui.width, c.comfyui.height = sw, sh
    return c


def describe(art) -> str:
    """The frame in words, for a prompt."""
    ratio = (getattr(art, "aspect_ratio", "") or looks.DEFAULT_ASPECT).strip()
    a = looks.aspect(ratio)
    if a["id"] == "16:9":
        return "16:9 横屏"
    return "9:16 竖屏"


def orientation(art) -> str:
    """vertical / horizontal - the word that goes into an English prompt."""
    return looks.orientation(getattr(art, "aspect_ratio", "") or looks.DEFAULT_ASPECT)


def composition(art) -> str:
    """The composition note that goes into a prompt."""
    ratio = (getattr(art, "aspect_ratio", "") or looks.DEFAULT_ASPECT).strip()
    if ratio == "16:9":
        return "horizontal composition, 16:9"
    return "vertical composition, 9:16"


def english_frame(ctx) -> str:
    """The frame in English, for an image prompt."""
    ad = ctx.project.art_direction
    ratio = (getattr(ad, "aspect_ratio", "") or looks.DEFAULT_ASPECT).strip()
    if ratio == "16:9":
        return "horizontal 16:9 frame"
    return "vertical 9:16 frame"


def prompt_frame(ctx) -> dict:
    """The frame, in the words a prompt needs.

    Every prompt that describes a picture says the same thing about the
    shape: the ratio, the size in pixels, and whether the frame stands up
    or lies down.  A prompt that leaves it out is a prompt that leaves the
    model to guess - and the guess is a wide picture for a vertical drama.
    """
    ad = ctx.project.art_direction
    w = int(getattr(ctx.cfg.compose, "width", 0) or 0)
    h = int(getattr(ctx.cfg.compose, "height", 0) or 0)
    ratio = (getattr(ad, "aspect_ratio", "") or looks.DEFAULT_ASPECT).strip()
    vertical = ratio != "16:9"
    if vertical:
        note = ("人物的头和身体落在画面中间，上下留出字幕和安全区，"
                "不要设计成横向宽幅构图，两个人不要并排站满一整行")
    else:
        note = "画面左右不要顶满，人物不要站在画面最边上"
    return {
        "aspect_ratio": ratio,
        "frame_size": (f"{w}×{h}" if w and h else ratio),
        "aspect_orientation": ("竖屏" if vertical else "横屏"),
        "frame_note": note,
    }
