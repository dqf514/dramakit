"""The skills that suit a look.

A look is a decision about how the drama looks - the frame, the
quality, the century - and it decides what the writing has to be good
at: a story set in the Republican era is written differently from a
sweet romance, and a comic is drawn differently from a film.

So each look carries the combination of skills that goes with it.  It
is a starting point, not a decision: the person can take anything off
it and add anything back, and what they leave alone is what the next
run writes with.
"""
from __future__ import annotations

# the core of every drama: the adaptation, the writing, the shots and
# the two prompt writers
_CORE = {
    "analyze": ["short-drama-novel-analyze", "short-drama-develop"],
    "script": ["short-drama-write",
               "screenwriting-theory/sw-format-adaptation",
               "screenwriting-theory/sw-scene-craft",
               "screenwriting-theory/sw-dialogue"],
    "storyboard": ["short-drama-storyboard"],
    "promptgen": ["short-drama-image-prompts", "short-drama-video-prompts"],
}

# what each family of looks asks for on top of that
_BY_GROUP = {
    # 民国、港风、年代戏：中国的剧集手艺
    "复古年代": {
        "script": ["screenwriting-theory/sw-chinese-series-practice",
                   "screenwriting-theory/sw-story-structure"],
    },
    # 仙侠、玄幻、水墨：先有前提和主题，再有场面
    "东方古装": {
        "script": ["screenwriting-theory/sw-premise-theme",
                   "screenwriting-theory/sw-chinese-series-practice",
                   "screenwriting-theory/sw-story-structure"],
    },
    # 悬疑、科幻：类型和解剖
    "悬疑未来": {
        "script": ["screenwriting-theory/sw-genre-anatomy",
                   "screenwriting-theory/sw-truby-anatomy",
                   "screenwriting-theory/sw-story-structure"],
    },
    # 甜宠、校园、治愈：人物和冲突，还有小津的调度
    "都市青春": {
        "script": ["screenwriting-theory/sw-character-conflict",
                   "screenwriting-theory/ozu-screenplay-style"],
    },
    # 动漫、三维：日本的写法，图像提示词是主角
    "二次元三维": {
        "script": ["screenwriting-theory/sw-japanese-screenwriting",
                   "screenwriting-theory/sw-scene-craft"],
        "promptgen": ["short-drama-image-prompts", "short-drama-video-prompts",
                      "screenwriting-theory/sw-korean-french-screenwriting"],
    },
    # 通用爆款：什么都可能发生的那一类
    "爆款通用": {
        "script": ["screenwriting-theory/sw-story-structure",
                   "screenwriting-theory/sw-character-conflict"],
    },
}

# the ones a single look asks for on top of its group
_BY_STYLE = {
    "republican": {"script": ["screenwriting-theory/sw-chinese-series-practice"]},
    "xianxia": {"script": ["screenwriting-theory/sw-premise-theme"]},
    "epic": {"script": ["screenwriting-theory/sw-premise-theme",
                         "screenwriting-theory/sw-story-structure"]},
    "noir": {"script": ["screenwriting-theory/sw-truby-anatomy"]},
    "cyberpunk": {"script": ["screenwriting-theory/sw-genre-anatomy"]},
    "sweet_comic": {"script": ["screenwriting-theory/sw-character-conflict"]},
    "youth": {"script": ["screenwriting-theory/sw-character-conflict",
                         "screenwriting-theory/ozu-screenplay-style"]},
    "documentary": {"script": ["screenwriting-theory/sw-scene-craft"]},
    "anime": {"script": ["screenwriting-theory/sw-japanese-screenwriting"]},
    "korean": {"script": ["screenwriting-theory/sw-korean-french-screenwriting",
                          "screenwriting-theory/sw-character-conflict"]},
}


def _merge(*parts: dict) -> dict:
    out: dict[str, list[str]] = {}
    for part in parts:
        for stage, names in (part or {}).items():
            row = out.setdefault(stage, [])
            for n in names or []:
                if n not in row:
                    row.append(n)
    return out


def skills_for_style(style_id: str, group: str = "") -> dict[str, list[str]]:
    """The skills that go with a look, by stage."""
    return _merge(_CORE, _BY_GROUP.get(group or "", {}),
                  _BY_STYLE.get(style_id or "", {}))


def by_style() -> dict:
    """Every look and the skills that go with it.

    The console shows this when the look changes: the skills that fit it
    are offered, and the person can take anything off and add anything
    back.
    """
    from ..ai.looks import STYLES
    out: dict[str, dict] = {}
    for s in STYLES:
        out[s["id"]] = {
            "name": s.get("name", s["id"]),
            "group": s.get("group", ""),
            "skills": skills_for_style(s["id"], s.get("group", "")),
        }
    return out
