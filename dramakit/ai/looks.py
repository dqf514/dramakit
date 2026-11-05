"""The two things a short drama is decided by before a word is written:
the shape of the frame, and the look of the picture.

Both were buried - one in a config file, the other in whatever the model
felt like that day - and both are asked for on every run.  So they are
written down here, in one place, where the console can offer them and the
pipeline can insist on them.

The look is a phrase in English, because that is what the picture models
read, and the name next to it is what a person recognises.  The frame is
the delivery size: the stills, the clips and the finished film are all
made in it, and a picture made in another shape is cropped to fit - and
the crop is what takes the faces off.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# The frame
# --------------------------------------------------------------------------- #
# A short drama is watched on a phone, so 9:16 is the default shape; 16:9 is
# what a drama made for a screen or a landscape player wants.
ASPECTS: list[dict] = [
    {
        "id": "9:16",
        "label": "9:16 竖屏",
        "orientation": "vertical",
        "note": "手机全屏，红果/抖音/视频号",
        "sizes": [
            {"id": "1080x1920", "label": "1080×1920", "w": 1080, "h": 1920},
            {"id": "768x1344", "label": "768×1344", "w": 768, "h": 1344},
            {"id": "720x1280", "label": "720×1280", "w": 720, "h": 1280},
            {"id": "1440x2560", "label": "1440×2560", "w": 1440, "h": 2560},
        ],
    },
    {
        "id": "16:9",
        "label": "16:9 横屏",
        "orientation": "horizontal",
        "note": "横屏，电视/网页/横版投放",
        "sizes": [
            {"id": "1920x1080", "label": "1920×1080", "w": 1920, "h": 1080},
            {"id": "1344x768", "label": "1344×768", "w": 1344, "h": 768},
            {"id": "1280x720", "label": "1280×720", "w": 1280, "h": 720},
            {"id": "3840x2160", "label": "3840×2160", "w": 3840, "h": 2160},
        ],
    },
]

DEFAULT_ASPECT = "9:16"
DEFAULT_SIZE = {"id": "1080x1920", "label": "1080×1920", "w": 1080, "h": 1920}


def aspect(aspect_ratio: str) -> dict:
    """The frame with that ratio, or the default one."""
    for a in ASPECTS:
        if a["id"] == (aspect_ratio or "").strip():
            return a
    return ASPECTS[0]


def size_for(aspect_ratio: str, width: int = 0, height: int = 0) -> tuple[int, int]:
    """The delivery size for a ratio.

    A project that says 9:16 and 1080×1920 gets exactly that.  A project
    that says 9:16 and nothing else gets the size that keeps the ratio
    and lands on a multiple of 16 - the sizes the video tools want.
    """
    a = aspect(aspect_ratio)
    for s in a["sizes"]:
        if width and height and s["w"] == width and s["h"] == height:
            return s["w"], s["h"]
    if width and height:
        return width, height
    d = DEFAULT_SIZE if a["id"] == DEFAULT_ASPECT else a["sizes"][0]
    return d["w"], d["h"]


def orientation(aspect_ratio: str) -> str:
    """vertical / horizontal, from the ratio itself."""
    a = aspect(aspect_ratio)
    if a["id"] == "16:9":
        return "horizontal"
    return "vertical"


# --------------------------------------------------------------------------- #
# The look
# --------------------------------------------------------------------------- #
# The looks that are running on the platforms now.  Each one is a phrase the
# picture models understand, and the era and palette that go with it - so
# picking one here also tells the analysis stage what world the drama lives
# in, instead of the model inventing one.
STYLES: list[dict] = [
    {
        "id": "cinematic",
        "group": "爆款通用",
        "name": "写实电影感",
        "tag": "通用爆款",
        "style": "写实电影感",
        "prompt": "cinematic realism, natural skin texture, dramatic key light, "
                  "shallow depth of field, subtle film grain",
        "era": "当代",
        "palette": "冷暖对比的电影调色，高光柔和",
    },
    {
        "id": "film",
        "group": "复古年代",
        "name": "胶片质感",
        "tag": "复古高级",
        "style": "胶片质感",
        "prompt": "35mm film still, visible film grain, slightly faded blacks, "
                  "soft halation around highlights, muted colors",
        "era": "当代",
        "palette": "低饱和的胶片色，暗部偏青",
    },
    {
        "id": "korean",
        "group": "爆款通用",
        "name": "韩系清冷写真",
        "tag": "甜宠当红",
        "style": "韩系清冷写真",
        "prompt": "Korean drama still, clean bright beauty lighting, soft "
                  "diffused key light, airy pastel palette, crisp modern look",
        "era": "当代",
        "palette": "通透的粉白色调，干净清亮",
    },
    {
        "id": "retro_hk",
        "group": "复古年代",
        "name": "港风复古",
        "tag": "复古怀旧",
        "style": "港风复古",
        "prompt": "1990s Hong Kong cinema still, tungsten street light, neon "
                  "signs glowing, dense urban night, heavy film grain",
        "era": "1990年代",
        "palette": "暖黄霓虹，浓重的夜色",
    },
    {
        "id": "republican",
        "group": "复古年代",
        "name": "民国年代戏",
        "tag": "年代大热",
        "style": "民国年代戏",
        "prompt": "Republican-era Chinese drama still, period studio lighting, "
                  "aged sepia tone, ornate wooden interiors, dust in the light",
        "era": "民国",
        "palette": "泛黄暖褐，做旧质感",
    },
    {
        "id": "sweet_comic",
        "group": "爆款通用",
        "name": "甜宠条漫",
        "tag": "霸总甜宠",
        "style": "甜宠条漫",
        "prompt": "modern Chinese webcomic illustration, clean flat cel "
                  "shading, soft blush palette, crisp linework, expressive faces",
        "era": "当代",
        "palette": "粉嫩暖色，奶油质感",
    },
    {
        "id": "anime",
        "group": "二次元三维",
        "name": "日系动漫",
        "tag": "二次元",
        "style": "日系动漫",
        "prompt": "Japanese anime film still, hand-painted cel shading, "
                  "vivid saturated colors, expressive lighting, detailed background art",
        "era": "当代",
        "palette": "高饱和的动画色，明亮通透",
    },
    {
        "id": "cartoon3d",
        "group": "二次元三维",
        "name": "3D动画",
        "tag": "合家欢",
        "style": "3D动画",
        "prompt": "3D animated feature film still, stylized character design, "
                  "soft global illumination, subsurface scattering, polished render",
        "era": "当代",
        "palette": "饱和的糖果色，柔和光影",
    },
    {
        "id": "ink",
        "group": "东方古装",
        "name": "国风水墨",
        "tag": "东方美学",
        "style": "国风水墨",
        "prompt": "Chinese ink wash painting style, delicate brush linework, "
                  "rice-paper texture, misty negative space, muted mineral colors",
        "era": "古代",
        "palette": "水墨灰与青绿，留白",
    },
    {
        "id": "xianxia",
        "group": "东方古装",
        "name": "仙侠唯美",
        "tag": "古装当红",
        "style": "仙侠唯美",
        "prompt": "Chinese xianxia fantasy still, ethereal rim light, drifting "
                  "mist and embers, flowing silk robes, dreamy bloom",
        "era": "古代",
        "palette": "冷蓝月白，霞光粉紫",
    },
    {
        "id": "cyberpunk",
        "group": "悬疑未来",
        "name": "赛博未来",
        "tag": "科幻",
        "style": "赛博未来",
        "prompt": "cyberpunk film still, rain-slick surfaces, neon cyan and "
                  "magenta signage, volumetric haze, high tech clutter",
        "era": "未来",
        "palette": "青紫霓虹，深黑底色",
    },
    {
        "id": "noir",
        "group": "悬疑未来",
        "name": "暗黑悬疑",
        "tag": "悬疑",
        "style": "暗黑悬疑",
        "prompt": "dark suspense thriller still, high contrast chiaroscuro "
                  "lighting, desaturated cold palette, hard shadows",
        "era": "当代",
        "palette": "近乎无彩的冷灰，只有一点血色",
    },
    {
        "id": "urban_warm",
        "group": "都市青春",
        "name": "都市暖光",
        "tag": "治愈",
        "style": "都市暖光",
        "prompt": "warm urban drama still, soft window light, gentle golden "
                  "hour tone, cozy everyday interior, clean modern look",
        "era": "当代",
        "palette": "暖黄米色，柔和过渡",
    },
    {
        "id": "documentary",
        "group": "都市青春",
        "name": "纪实手持",
        "tag": "真实感",
        "style": "纪实手持",
        "prompt": "documentary photography, handheld camera, available daylight, "
                  "imperfect framing, fine 16mm grain, honest reportage look",
        "era": "当代",
        "palette": "中性自然色，轻微偏青",
    },
    {
        "id": "epic",
        "group": "东方古装",
        "name": "玄幻史诗",
        "tag": "大场面",
        "style": "玄幻史诗",
        "prompt": "epic fantasy film still, monumental scale, dramatic god rays "
                  "through clouds, gold and deep blue palette, grand costume design",
        "era": "古代",
        "palette": "深蓝与鎏金",
    },
    {
        "id": "youth",
        "group": "都市青春",
        "name": "青春校园",
        "tag": "校园",
        "style": "青春校园",
        "prompt": "youth campus drama still, bright afternoon sun through trees, "
                  "fresh natural colors, candid youthful energy",
        "era": "当代",
        "palette": "清新的白绿蓝",
    },
]


def style(style_id: str) -> dict:
    """The look with that id, or the default one."""
    for s in STYLES:
        if s["id"] == (style_id or "").strip():
            return s
    return STYLES[0]


def style_by_name(name: str) -> dict | None:
    """The look with that Chinese name - a project that was analysed before
    the console knew about looks still has a style written on it."""
    n = (name or "").strip()
    if not n:
        return None
    for s in STYLES:
        if s["name"] == n or s["style"] == n:
            return s
    return None


def looks() -> dict:
    """What the console offers: the frames, the looks, and the defaults."""
    return {
        "aspects": ASPECTS,
        "styles": STYLES,
        "default_aspect": DEFAULT_ASPECT,
        "default_size": DEFAULT_SIZE,
    }
