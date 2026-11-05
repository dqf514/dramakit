"""What the skills are, so a person can choose between them.

The stages load rules from documents under skills/ - a folder per skill, a
SKILL.md inside it - and the choice lived in a YAML file nobody could see.
A skill says what it is in its own frontmatter, so the list reads itself:
name, summary, how much text it would add to a prompt.

That last number is the reason to look. A stage sends its skills with
every call, and the prompt stage was measured at ten thousand characters
per shot because two of them were always on. What a skill costs is not
something to discover from a stopwatch.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "skills"

# the stages that load skills, and the config key each one reads
STAGES = ("analyze", "script", "storyboard", "promptgen")

# a skill folder is named for its family: short-drama-write, and the
# theory skills are nested one deeper under screenwriting-theory
FAMILY_ZH = {
    "short-drama": "短剧通用",
    "short-drama-novel-analyze": "小说解析",
    "short-drama-write": "编剧",
    "short-drama-storyboard": "分镜",
    "short-drama-image-prompts": "出图提示词",
    "short-drama-video-prompts": "视频提示词",
    "short-drama-assets": "资产",
    "short-drama-produce": "制片",
    "short-drama-review": "审片",
    "short-drama-edit": "剪辑",
    "short-drama-develop": "开发",
    "screenwriting-theory": "编剧理论",
}

# The theory skills carry English names in their frontmatter, which is fine
# for a model and unreadable for a person choosing between them.
TITLE_ZH = {
    "screenwriting-theory/chekhov-dramaturgy": "契诃夫式剧作",
    "screenwriting-theory/ozu-screenplay-style": "小津式调度",
    "screenwriting-theory/succession-series-writing": "权谋剧集写作",
    "screenwriting-theory/sw-american-case-studies": "美剧案例",
    "screenwriting-theory/sw-character-conflict": "人物冲突",
    "screenwriting-theory/sw-chinese-opera-banqiang": "板腔剧作",
    "screenwriting-theory/sw-chinese-opera-banqiang-cases": "板腔剧作案例",
    "screenwriting-theory/sw-chinese-opera-qupai": "曲牌剧作",
    "screenwriting-theory/sw-chinese-opera-qupai-cases": "曲牌剧作案例",
    "screenwriting-theory/sw-chinese-series-practice": "华语剧集实践",
    "screenwriting-theory/sw-dialogue": "台词写作",
    "screenwriting-theory/sw-format-adaptation": "形式改编",
    "screenwriting-theory/sw-genre-anatomy": "类型解剖",
    "screenwriting-theory/sw-industry-business": "行业与商业",
    "screenwriting-theory/sw-japanese-screenwriting": "日式编剧",
    "screenwriting-theory/sw-korean-french-screenwriting": "韩法编剧",
    "screenwriting-theory/sw-premise-theme": "前提与主题",
    "screenwriting-theory/sw-scene-craft": "场景写作",
    "screenwriting-theory/sw-series-case-studies": "剧集案例",
    "screenwriting-theory/sw-series-engine-bible": "剧集引擎圣经",
    "screenwriting-theory/sw-series-structure": "剧集结构",
    "screenwriting-theory/sw-sitcom-comedy": "情景喜剧",
    "screenwriting-theory/sw-story-structure": "故事结构",
    "screenwriting-theory/sw-truby-anatomy": "特里比结构",
    "screenwriting-theory/sw-workflow": "编剧流程",
    "screenwriting-theory/sw-writers-room": "编剧室协作",
}


def _frontmatter(text: str) -> dict:
    """The YAML-ish header of a SKILL.md: name, description, license.

    Not a real YAML parse - these files carry a two-line header and prose
    that would need quoting to be valid, and a parser that rejects a skill
    over a stray colon would take the whole page down.
    """
    out: dict = {}
    if not text.lstrip().startswith("---"):
        return out
    end = text.find("\n---", 3)
    if end < 0:
        return out
    for line in text[3:end].split("\n"):
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    return out


def _family(rel: Path) -> tuple[str, str]:
    """A skill's family: the folder it sits in, and its display name."""
    parts = rel.parts
    if len(parts) == 1:
        key = parts[0]
        return key, FAMILY_ZH.get(key, key)
    key = parts[0]
    # the theory skills are one skill each, not a family of their own
    return key, FAMILY_ZH.get(key, key)


def _reference_files(folder: Path) -> list[Path]:
    """The documents that go with a skill.

    Two shapes are in use: a `references/` folder, and a `reference.md`
    beside the SKILL.md itself.
    """
    out: list[Path] = []
    refs = folder / "references"
    if refs.is_dir():
        out += sorted(refs.glob("*.md"))
    out += sorted(folder.glob("reference*.md"))
    return out


def catalog() -> list[dict]:
    """Every skill a stage could load, with what choosing it costs.

    Sorted by family then name, so the page groups itself. A skill whose
    SKILL.md is missing is skipped: it could not be loaded either.
    """
    if not ROOT.exists():
        return []
    out: list[dict] = []
    for md in sorted(ROOT.rglob("SKILL.md")):
        rel = md.parent.relative_to(ROOT)
        text = md.read_text(encoding="utf-8", errors="replace")
        fm = _frontmatter(text)
        body = text
        if text.lstrip().startswith("---"):
            e = text.find("\n---", 3)
            if e > 0:
                body = text[e + 4:]
        fam, fam_zh = _family(rel)
        refs = _reference_files(md.parent)
        out.append({
            "name": rel.as_posix(),
            "title": fm.get("name") or rel.name,
            "title_zh": TITLE_ZH.get(rel.as_posix(), ""),
            "description": fm.get("description") or "",
            "family": fam,
            "family_zh": fam_zh,
            # what it adds to a prompt, and what it would add with the
            # deeper references that nothing asks for yet
            "chars": len(body),
            "ref_chars": sum(len(f.read_text(encoding="utf-8", errors="replace"))
                             for f in refs),
            "refs": len(refs),
            # the name of every reference, so a stage can ask for one of
            # them by name
            "ref_names": [f.name for f in refs],
        })
    return out


def cost(selection: dict[str, list[str]],
         refs: dict[str, dict[str, list[str]]] | None = None) -> dict[str, int]:
    """Characters each stage would add, given what is selected.

    Shown before a run: a stage sends these with every call, so a list
    that looks harmless is a multiplier on the whole batch.

    `refs` is the per-stage map of the references that are actually sent
    with those skills - the documents are part of the cost, and a number
    that leaves them out would be a lie.
    """
    by_name = {s["name"]: s for s in catalog()}
    out: dict[str, int] = {}
    for stage, names in (selection or {}).items():
        total = 0
        stage_refs = (refs or {}).get(stage) or {}
        for n in names or []:
            s = by_name.get(n)
            if not s:
                continue
            total += s["chars"]
            wanted = stage_refs.get(n)
            if not wanted:
                continue
            by_ref = {r["name"]: r["chars"] for r in _reference_chars()}
            for name in wanted:
                chars = by_ref.get(f"{n}/{name}")
                if chars:
                    total += chars
        out[stage] = total
    return out


def _reference_chars() -> list[dict]:
    """Every reference document, with its size, keyed by skill and name."""
    out: list[dict] = []
    if not ROOT.exists():
        return out
    for md in sorted(ROOT.rglob("SKILL.md")):
        rel = md.parent.relative_to(ROOT)
        for f in _reference_files(md.parent):
            out.append({
                "name": f"{rel.as_posix()}/{f.name}",
                "chars": len(f.read_text(encoding="utf-8", errors="replace")),
            })
    return out
