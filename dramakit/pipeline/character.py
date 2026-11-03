"""Stage 3 — character: lock every character's look before storyboarding.

Produces two things that the downstream stages reuse verbatim:
  * `anchor_prompt` — a stable English block (face, hair, outfit) injected at the
    front of every shot prompt
  * reference images — front / side / three-quarter portraits generated with a
    per-character fixed seed, so a human can eyeball and lock the cast

If ComfyUI is off or unreachable the anchors are still written, so prompt-only
consistency keeps working.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import Config
from ..models import Character, Location, Status
from ..project import ProjectStore
from ..prompts import templates as T
from ..seasons import LOOK_FIELDS, snapshot_look
from .base import Context

VIEW_TEXT = {
    "front": "front view, facing the camera, neutral standing pose",
    "face": "tight close-up of the face, the face filling the frame",
    "side": "side profile view, facing left, neutral standing pose",
    "three_quarter": "three-quarter view, slight body angle, neutral standing pose",
    "back": "back view, seen from behind, neutral standing pose",
}

# FLUX 3 reads a scene caption, not a tag list, and it takes "reference
# sheet" literally - the old wording came back as technical line art.
FLUX3_VIEW = {
    "front": "seen from the front, facing the camera, standing at ease",
    "face": ("seen in a tight head-and-shoulders close-up, the face filling "
             "the frame and looking straight into the camera, every feature "
             "sharp and unobstructed"),
    "side": "seen from the side in profile, facing left, standing at ease",
    "three_quarter": "seen from a three-quarter angle, body slightly turned, standing at ease",
    "back": "seen from behind, back turned to the camera, standing at ease",
}


def _has_refs_on_disk(ctx: Context, c: Character) -> bool:
    """True when this character already has reference pictures on disk."""
    return any(ctx.store.abs(r).exists() for r in c.refs())


def record_season_looks(ctx: Context, chars: list[Character]) -> None:
    """Write this season's looks into the canon, for the seasons after it.

    The canon is what lets season 3 know that 余飞 was already a tree by the
    end of season 1, and what voice he has had the whole time. Identity and
    voice are stored once and carried forward; the look is appended per
    season, so the evolution is readable rather than lost.
    """
    canon = ctx.project.canon
    season = ctx.season_index
    for c in chars:
        # identity + voice travel through unchanged
        canon.characters[c.name] = {
            "role": c.role, "gender": c.gender, "aliases": list(c.aliases),
            "personality": c.personality, "locked": c.locked,
        }
        if c.voice_id:
            canon.voices[c.name] = c.voice_id
        looks = canon.character_looks.setdefault(c.name, [])
        look = snapshot_look(c)
        # one look per season; a rerun of the same season replaces its own
        pos = season - 1 if season > 0 else len(looks)
        while len(looks) <= pos:
            looks.append({})
        looks[pos] = look


def _seed(name: str, view: str) -> int:
    digest = hashlib.sha1(f"{name}:{view}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % (2**31)


def _fallback_anchor(c: Character) -> str:
    bits = [c.visual_prompt or c.appearance, c.hair, c.outfit]
    return ", ".join(b.strip().rstrip(",") for b in bits if b and b.strip())


def build_anchors(ctx: Context, chars: list[Character]) -> int:
    """Fill missing anchor prompts (LLM first, deterministic fallback second)."""
    if not chars:
        return 0
    cfg = ctx.cfg.characters
    before = sum(1 for c in chars if c.anchor_prompt)
    pending = [c for c in chars if not c.anchor_prompt and not c.locked]
    if pending and cfg.use_llm_anchor:
        lines = "\n".join(
            f"- name: {c.name}; role: {c.role}; gender: {c.gender}; age: {c.age}; "
            f"appearance: {c.appearance}; visual_prompt: {c.visual_prompt}; "
            f"outfit: {c.outfit}; hair: {c.hair}; locked: {c.locked}"
            for c in pending)
        try:
            llm = ctx.providers.llm_for("promptgen")
            data = llm.complete_json(
                T.CHARACTER_SHEET_SYSTEM,
                T.render(T.CHARACTER_SHEET_USER, characters=lines,
                         max_chars=cfg.anchor_max_chars))
            if isinstance(data, list):
                data = {"characters": data}
            by_name = {str(x.get("name", "")).strip(): x
                       for x in (data.get("characters") or []) if isinstance(x, dict)}
            for c in pending:
                item = by_name.get(c.name)
                if not item:
                    continue
                anchor = str(item.get("anchor_prompt") or "").strip()
                if anchor:
                    c.anchor_prompt = anchor[: cfg.anchor_max_chars]
                neg = str(item.get("negative_prompt") or "").strip()
                if neg:
                    c.negative_prompt = neg
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("character: 角色锚点 LLM 失败(%s)，用设定兜底", str(e)[:160])
    made = 0
    for c in chars:
        if not c.anchor_prompt:
            c.anchor_prompt = _fallback_anchor(c)[: cfg.anchor_max_chars]
            made += 1
    return max(made, sum(1 for c in chars if c.anchor_prompt) - before)


def _ref_prompt(ctx: Context, c: Character, view: str,
                derived: bool = False) -> str:
    ad = ctx.project.art_direction
    style = ad.style_prompt_prefix or ad.style or "cinematic realistic"
    if derived:
        # the same person as in the reference picture, only turned
        return (
            f"Full-color studio photograph, the same person as in the "
            f"reference picture - identical face, identical hair, identical "
            f"clothes - now {FLUX3_VIEW.get(view, FLUX3_VIEW['front'])}. "
            f"The whole body is visible from head to feet, centered in the "
            f"frame with a little space around it, photographed against a plain "
            f"light gray seamless backdrop, soft even light from the front, "
            f"natural skin texture and fabric detail, a neutral expression, "
            f"no props, no text, no watermark, {style}."
        )
    if view == "four":
        # One picture carrying everything the shots need: the face large
        # enough to hold an identity, and the three body views beside it.
        # Two pictures meant two references per person per shot, and the
        # face sharing a frame with three bodies is a face too small to
        # keep the same - this puts it on its own half of one image.
        return (
            f"Character reference sheet, a single wide studio photograph "
            f"containing four views of the same person: on the left a large "
            f"high-resolution close-up of the head filling that half of the "
            f"frame, and on the right three full-body figures standing in a "
            f"row - seen from the front, from the side in profile, and from "
            f"behind. {c.anchor()} The same person in all four views, with "
            f"identical face, identical hairstyle, identical clothing and "
            f"identical body proportions throughout. Premium neutral grey "
            f"studio backdrop with soft even lighting, clean uncluttered "
            f"composition, natural skin texture and fabric detail, "
            f"a neutral expression, no props, no labels, no text, no "
            f"watermark, {style}."
        )
    if view == "face":
        # the face, filling the frame: this is the picture that keeps the
        # face the same from one shot to the next
        if derived:
            return (
                f"Full-color studio photograph, the same face as in the "
                f"reference picture - identical face, identical hair, "
                f"identical clothes - now a tight head-and-shoulders close-up. "
                f"The face fills the frame, looking straight into the camera, "
                f"every feature sharp and unobstructed, photographed against a "
                f"plain light gray seamless backdrop, soft even light from the "
                f"front, natural skin texture, no props, no text, no "
                f"watermark, {style}."
            )
        return (
            f"Full-color studio photograph, a tight head-and-shoulders "
            f"close-up portrait of {c.anchor()}, "
            f"{FLUX3_VIEW['face']}. The face fills the frame, every feature "
            f"sharp and unobstructed, photographed against a plain light gray "
            f"seamless backdrop, soft even light from the front, natural skin "
            f"texture, a neutral expression, no props, no text, no watermark, "
            f"{style}."
        )
    if ctx.cfg.comfyui.prompt_format == "flux3":
        return (
            f"Full-color studio photograph, full-body portrait of {c.anchor()}, "
            f"{FLUX3_VIEW.get(view, FLUX3_VIEW['front'])}. The whole body is "
            f"visible from head to feet, centered in the frame with a little "
            f"space around it, photographed against a plain light gray seamless "
            f"backdrop, soft even light from the front, natural skin texture and "
            f"fabric detail, a neutral expression, no props, no text, no "
            f"watermark, {style}."
        )
    return (
        f"character reference sheet, {c.anchor()}, "
        f"{VIEW_TEXT.get(view, VIEW_TEXT['front'])}, full body, "
        f"plain light gray studio background, soft even lighting, "
        f"{style}, highly detailed, no text, no watermark"
    )


def _loc_prompt(ctx: Context, loc: Location) -> str:
    ad = ctx.project.art_direction
    style = ad.style_prompt_prefix or ad.style or "cinematic realistic"
    desc = loc.visual_prompt or loc.description or loc.name
    if ctx.cfg.comfyui.prompt_format == "flux3":
        return (
            f"Full-color photograph, a wide establishing view of {desc}. "
            f"The space is empty - no people, no figures, no text anywhere. "
            f"{ad.era}, {style}, the architecture and the furnishings are what "
            f"the picture is about, even daylight, sharp from edge to edge."
        )
    return (
        f"location reference photo, empty scene, {desc}, "
        f"no people, no text, no watermark, {ad.era}, {style}, "
        f"wide establishing view, consistent architecture, highly detailed"
    )


def generate_location_refs(ctx: Context) -> int:
    """Generate one establishing reference image per location. Never raises."""
    cfg = ctx.cfg.characters
    vis = ctx.providers.visual
    if vis is None or not ctx.project.locations:
        return 0
    if hasattr(vis, "ping") and not vis.ping():
        ctx.log.warning("character: ComfyUI 不可达，跳过场景参考图")
        return 0
    ccfg = ctx.cfg.comfyui
    negative = "people, person, crowd, text, watermark, logo, blurry, distorted"
    made = 0
    for loc in ctx.project.locations:
        existing = [r for r in loc.ref_images
                    if ctx.store.abs(r).exists()]
        if existing:
            loc.ref_images = existing
            continue
        out = ctx.store.location_ref_path(loc.name)
        try:
            vis.generate_image(
                prompt=_loc_prompt(ctx, loc), negative=negative,
                width=cfg.ref_width, height=cfg.ref_height,
                seed=_seed("loc:" + loc.name, "ref"), steps=ccfg.steps, cfg=ccfg.cfg,
                out_path=str(out),
                extra={"sampler": ccfg.sampler, "scheduler": ccfg.scheduler,
                       "checkpoint": ccfg.checkpoint})
            rel = ctx.store.rel(out)
            loc.ref_images = [rel]
            made += 1
            ctx.log.info("character: 场景 %s 参考图已生成", loc.name)
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("character: 场景 %s 出图失败 %s", loc.name, str(e)[:160])
    return made


def differentiate_characters(ctx: Context, chars: list[Character]) -> int:
    """Two characters that look the same come out as copies.

    Same gender, the same age written, the same hair, the same
    temperament - and the two faces come out of the model as one face
    twice.  The fix is before the pictures: compare the characters on a
    few dimensions, and change the ones that match too much.
    """
    if len(chars) < 2:
        return 0
    llm = ctx.providers.llm_for("character")
    lines = "\n".join(
        f"- name: {c.name}; role: {c.role}; gender: {c.gender}; age: {c.age}; "
        f"appearance: {c.appearance}" for c in chars)
    try:
        data = llm.complete_json(
            "你是短剧的选角导演。你要看的是一群角色会不会长得太像。"
            "只输出JSON。",
            "下面是这部短剧的角色：\n" + lines + "\n\n"
            "找出**看起来会像同一个人的角色对**：同性别、年龄相仿、发型相仿、"
            "气质相近的两个人，看镜头会让观众分不清谁是谁。\n"
            "对每一对，给出其中**后一个**角色的新外貌描述（中文），"
            "要明确改掉年龄感、发型、体型、气质里的至少两项，"
            "但保持他的身份、年龄大方向和角色功能不变。\n"
            "只输出JSON：{\"pairs\":[{\"a\":\"角色名\",\"b\":\"角色名\","
            "\"appearance\":\"新的外貌描述\"}]}")
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("character: 角色相似度检查失败(%s)", str(e)[:120])
        return 0
    if isinstance(data, list):
        data = data[0] if data else {}
    by_name = {c.name: c for c in chars}
    changed = 0
    for pair in (data.get("pairs") or []):
        if not isinstance(pair, dict):
            continue
        a = str(pair.get("a") or "").strip()
        b = str(pair.get("b") or "").strip()
        text = str(pair.get("appearance") or "").strip()
        if a not in by_name or b not in by_name or not text:
            continue
        c = by_name[b]
        ctx.log.warning("character: %s 和 %s 太像了，把 %s 的外貌改成：%s",
                        a, b, b, text[:120])
        c.appearance = text[:400]
        c.anchor_prompt = ""       # the anchor is built from the appearance
        changed += 1
    if changed:
        build_anchors(ctx, [by_name[str(p.get("b"))] for p in (data.get("pairs") or [])
                            if isinstance(p, dict) and str(p.get("b")) in by_name])
    return changed


def _view_size(ctx: Context, view: str) -> tuple[int, int]:
    """The size of one reference picture.

    The face fills a wide frame - a face in a portrait frame has gray on
    both sides.  The body views are the other way round: a full body in a
    wide frame is a small person in a field of gray, and that gray is what
    ends up in the picture.  The four-view sheet is wide on purpose: a
    head on one side and three figures on the other cannot be arranged any
    other way round.
    """
    cfg = ctx.cfg.characters
    if view == "four":
        return int(getattr(cfg, "ref_four_width", 1536)), \
               int(getattr(cfg, "ref_four_height", 768))
    if view == "face":
        return int(cfg.ref_width), int(cfg.ref_height)
    return int(cfg.ref_body_width), int(cfg.ref_body_height)


# The sentence every voice sample is read in. The same one for everyone:
# what is being compared is the voice, so if the words differ the
# difference is the script rather than the person.
VOICE_SAMPLE = ("这是角色的声音样本。用你平时说话的语气，"
                "自然地把这句话读出来，语速适中，情绪平稳。")


def generate_voice_refs(ctx: Context, chars: list[Character]) -> int:
    """Record one sample of each character's voice, once.

    The video model speaks the words and takes the timbre from a recording,
    so a character is only consistent across clips if the same recording is
    handed over every time. Made here, with the rest of the character, so
    the picture machine never has to wait for the voice machine to start.

    Never raises: a voice that cannot be recorded is a voice without a
    sample, and the shot falls back to its own line rather than failing
    the stage.
    """
    tts = ctx.providers.tts
    if tts is None:
        ctx.log.info("character: 没有 TTS，跳过声音样本")
        return 0
    made = 0
    for c in chars:
        if not c.voice_id:
            continue
        out = ctx.store.character_voice_path(c.name)
        if c.voice_ref and ctx.store.abs(c.voice_ref).exists():
            continue
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            tts.synthesize(VOICE_SAMPLE, c.voice_id, str(out))
            if out.exists() and out.stat().st_size > 0:
                c.voice_ref = ctx.store.rel(out)
                made += 1
                ctx.log.info("character: %s 声音样本已生成", c.name)
            else:
                ctx.log.warning("character: %s 声音样本是空的", c.name)
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("character: %s 声音样本失败: %s", c.name, str(e)[:120])
    return made


def generate_refs(ctx: Context, c: Character, views: list[str] | None = None) -> int:
    """Generate reference portraits for one character. Never raises.

    The pictures go into this season's own folder, so a look that changed
    in season 3 does not overwrite the face season 1 was drawn with - an
    episode keeps the reference it was made with, for as long as anyone
    wants to re-render it.

    A locked character is skipped: a locked look is the user's decision
    and its pictures were already made. Re-drawing it would hand back a
    different face under a name that is supposed to be fixed.
    """
    cfg = ctx.cfg.characters
    season = ctx.season_index
    vis = ctx.providers.visual
    if vis is None:
        ctx.log.info("character: 未启用画面 provider，跳过 %s 的三视图", c.name)
        return 0
    # The pictures are already there, so there is nothing to make - and
    # drawing them again would replace the set the rest of the project was
    # made with. A lock is not the test: a look that exists is kept, a look
    # that does not is drawn, which is what the stage is for.
    if _has_refs_on_disk(ctx, c):
        ctx.log.info("character: %s 参考图已在，跳过重画", c.name)
        return 0
    if hasattr(vis, "ping") and not vis.ping():
        ctx.log.warning("character: ComfyUI 不可达，跳过 %s 的三视图", c.name)
        return 0
    views = views or cfg.ref_views or ["front"]
    ccfg = ctx.cfg.comfyui
    negative = ", ".join(x for x in (c.negative_prompt,
                                     "different person, inconsistent face, extra limbs, text, watermark")
                         if x)
    made = 0
    master = ""
    for view in views:
        ctx.check_stop()   # 一图一问：一张约 24 秒
        out = ctx.store.character_ref_path(c.name, view, "png", season=season)
        try:
            # the first view is the master; the other views are made from
            # it, so the four panels are one person
            refs = [master] if master else []
            vw, vh = _view_size(ctx, view)
            vis.generate_image(
                prompt=_ref_prompt(ctx, c, view, derived=bool(master)),
                negative=negative,
                width=vw, height=vh,
                seed=_seed(c.name, view), steps=ccfg.steps, cfg=ccfg.cfg,
                out_path=str(out),
                extra={"sampler": ccfg.sampler, "scheduler": ccfg.scheduler,
                       "checkpoint": ccfg.checkpoint},
                ref_images=refs)
            rel = ctx.store.rel(out)
            if rel not in c.ref_images:
                c.ref_images.append(rel)
            if not c.ref_sheet:
                c.ref_sheet = rel
            if not master:
                master = str(out)
            made += 1
            ctx.log.info("character: %s %s 参考图已生成", c.name, view)
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("character: %s %s 出图失败 %s", c.name, view, str(e)[:160])
    return made


def _fallback_voice(c: Character, voices: list[str]) -> str:
    if not voices:
        return ""
    female = ("女", "female")
    male = ("男", "male")
    # MiniMax ids say the gender up front; edge ids need the name list
    if c.gender in female:
        pref = [v for v in voices if v.startswith("female-")]
        if not pref:
            pref = [v for v in voices if "female" in v.lower()]
        if pref:
            return pref[0]
    elif c.gender in male:
        pref = [v for v in voices if v.startswith("male-")]
        if not pref:
            pref = [v for v in voices if "male" in v.lower()]
        if pref:
            return pref[0]
    prefs = []
    if c.gender in female:
        prefs = ["Xiaoxiao", "Xiaoyi", "Xiaochen", "Xiaohan", "Xiaomeng",
                 "Xiaomo", "Xiaoxuan", "Xiaoyan"]
    elif c.gender in male:
        prefs = ["Yunxi", "Yunjian", "Yunye", "Yunyang", "Yunfeng", "Yunhao"]
    for name in prefs:
        for voice in voices:
            if name.lower() in voice.lower():
                return voice
    return voices[0]


# 标准普通话音色的气质备注：喂给配音导演 LLM，让它按年龄/气质挑
VOICE_NOTES: dict[str, str] = {
    "zh-CN-YunxiNeural": "青年男声，阳光清朗，适合男主/少年",
    "zh-CN-YunjianNeural": "青年男声，硬朗有力，适合硬汉/战神/狠角色",
    "zh-CN-YunxiaNeural": "少年男声，稚气，适合弟弟/学生",
    "zh-CN-YunyangNeural": "成年男声，成熟稳重有分量，适合长辈/反派/老板",
    "zh-CN-XiaoxiaoNeural": "青年女声，温柔标准，适合女主",
    "zh-CN-XiaoyiNeural": "少女女声，甜美活泼，适合少女/甜宠",
    # --- MiniMax 系统音色（支持情感参数，短剧首选）---
    "male-qn-qingse": "青年男声，清澈干净，适合男主/少年/学生",
    "male-qn-jingying": "青年男声，精英干练，适合豪门少爷/职场精英",
    "male-qn-badao": "青年男声，霸道强势，适合反派/霸总",
    "male-qn-daxuesheng": "青年男声，阳光学生气，适合学生/弟弟",
    "female-shaonv": "少女女声，清甜有活力，适合女主/妹妹",
    "female-yujie": "女声，御姐成熟，适合大女主/女强人",
    "female-chengshu": "女声，温柔成熟，适合母亲/知性女性",
    "female-tianmei": "女声，甜美柔和，适合甜宠/女主",
    "Chinese (Mandarin)_Gentleman": "男声，温润儒雅，适合男主/gentleman",
    "Chinese (Mandarin)_Lyrical_Voice": "男声，抒情有磁性，适合深情男主",
    "Chinese (Mandarin)_Sincere_Adult": "男声，真诚沉稳，适合认真角色",
    "Chinese (Mandarin)_Unrestrained_Young_Man": "男声，不羁洒脱，适合反叛角色",
    "Chinese (Mandarin)_Stubborn_Friend": "男声，嘴硬倔强，适合损友/硬汉",
    "Chinese (Mandarin)_Male_Announcer": "男声，播报腔，适合旁白/解说",
    "Chinese (Mandarin)_News_Anchor": "女声，新闻播报，适合旁白/解说",
    "Chinese (Mandarin)_Reliable_Executive": "男声，沉稳高管，适合上位者",
    "Chinese (Mandarin)_Humorous_Elder": "男声，长者带笑意，适合慈祥长辈",
    "Chinese (Mandarin)_Kind-hearted_Elder": "女声，慈祥长者，适合奶奶",
    "Chinese (Mandarin)_Gentle_Senior": "女声，温柔学姐/长者",
    "Chinese (Mandarin)_Warm_Bestie": "女声，温暖闺蜜，适合女主/姐妹",
    "Chinese (Mandarin)_Wise_Women": "女声，阅历感，适合姐姐/长辈",
    "Chinese (Mandarin)_Sweet_Lady": "女声，甜美清亮，适合甜美女主",
    "Chinese (Mandarin)_Mature_Woman": "女声，傲娇御姐，适合强势女性",
    "Chinese (Mandarin)_Warm_Girl": "少女女声，温暖治愈，适合女主",
    "Chinese (Mandarin)_Crisp_Girl": "少女女声，清脆爽朗，适合活泼角色",
    "Chinese (Mandarin)_Soft_Girl": "少女女声，柔软温顺，适合柔弱角色",
    "Chinese (Mandarin)_Pure-hearted_Boy": "少年男声，清澈邻家，适合少年",
    "Chinese (Mandarin)_Straightforward_Boy": "少年男声，率真，适合弟弟",
    "Chinese (Mandarin)_Radio_Host": "男声，电台主播，适合旁白",
    "presenter_male": "男声，播音主持，适合旁白/解说",
    "presenter_female": "女声，播音主持，适合旁白/解说",
    "audiobook_male_1": "男声，有声书主播，适合旁白/叙述",
    "audiobook_female_1": "女声，有声书主播，适合旁白/叙述",
    "badao_shaoye": "男声，霸道少爷，适合豪门男主/反派",
    "lengdan_xiongzhang": "男声，冷淡学长，适合高冷角色",
    "junlang_nanyou": "男声，俊朗，适合男主",
    "danya_xuejie": "女声，淡雅学姐，适合知性女性",
}

# 内置兜底音色池：provider 音色表拉取失败时用（edge-tts 偶尔被网络抖动打空）
FALLBACK_VOICES: list[str] = [
    "zh-CN-YunxiNeural", "zh-CN-YunjianNeural", "zh-CN-YunxiaNeural",
    "zh-CN-YunyangNeural", "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural",
]


def _curated_voices(ctx: Context, voices: list[str]) -> tuple[list[str], str]:
    """Filter the provider voice list down to a usable, annotated pool.

    Keeps only the configured locales (default: standard Mandarin, no dialects)
    so the casting LLM cannot pick a Cantonese/Taiwanese voice for a mainland
    drama, and annotates each voice with its age/timbre.
    """
    cfg = ctx.cfg.tts
    pool = [v for v in voices if v not in set(cfg.voice_exclude or [])]
    if cfg.voice_pool:
        allowed = set(cfg.voice_pool)
        pool = [v for v in pool if v in allowed]
    elif cfg.provider == "edge":
        locs = cfg.voice_locales or ["zh-CN"]
        pool = [v for v in pool
                if any(v.startswith(f"{loc}-") and len(v.split("-")) == 3 for loc in locs)]
    # other providers already hand back a curated list (MiniMax returns the
    # Chinese system voices), so there is nothing to filter by locale
    notes = {**VOICE_NOTES, **(cfg.voice_notes or {})}
    listed = "\n".join(f"- {v}" + (f"   # {notes[v]}" if v in notes else "")
                       for v in pool)
    return pool, listed


def cast_voices(ctx: Context, chars: list[Character]) -> int:
    """Assign a TTS voice to every character without one (LLM, then gender map)."""
    cfg = ctx.cfg.characters
    if not cfg.auto_cast:
        return 0
    pending = [c for c in chars if not c.voice_id]
    if not pending:
        return 0
    try:
        voices = ctx.providers.tts.list_voices()
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("character: 读取音色失败(%s)，改用内置兜底音色池", str(e)[:120])
        voices = []
    voices, voices_doc = _curated_voices(ctx, voices)
    if not voices:
        # provider 音色表为空（网络抖动/服务不可用）：退回内置池，别让整集选角失败
        voices, voices_doc = _curated_voices(ctx, FALLBACK_VOICES)
        ctx.log.warning("character: 音色表不可用，使用内置兜底音色池")
    if not voices:
        return 0
    lines = "\n".join(
        f"- name: {c.name}; role: {c.role}; gender: {c.gender}; age: {c.age}; "
        f"personality: {c.personality}" for c in pending)
    ad = ctx.project.art_direction
    try:
        llm = ctx.providers.llm_for("script")
        data = llm.complete_json(
            T.VOICE_CAST_SYSTEM,
            T.render(T.VOICE_CAST_USER, characters=lines, voices=voices_doc,
                     genre=ad.genre or "", style=ad.style or "", era=ad.era or "",
                     tone=ad.color_palette or ""))
        if isinstance(data, list):
            data = {"characters": data}
        by_name = {str(x.get("name", "")).strip(): x
                   for x in (data.get("characters") or []) if isinstance(x, dict)}
        taken: set[str] = set()
        for c in pending:
            got = by_name.get(c.name, {})
            picked = str(got.get("voice_id", "")).strip()
            # two characters sharing one voice read as the same person
            if picked in voices and picked not in taken:
                c.voice_id = picked
                c.voice_pitch = str(got.get("pitch", "")).strip()
                c.voice_rate = str(got.get("rate", "")).strip()
                taken.add(picked)
        # the LLM happily gives two characters the same voice; hand the
        # leftovers a different one from the pool
        free = [v for v in voices if v not in taken]
        for c in pending:
            if c.voice_id:
                continue
            if not free:
                break
            c.voice_id = free.pop(0)
            c.voice_pitch = c.voice_pitch or ""
            c.voice_rate = c.voice_rate or ""
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("character: 自动选角 LLM 失败(%s)，按性别兜底", str(e)[:120])
    made = 0
    for c in pending:
        if not c.voice_id:
            c.voice_id = _fallback_voice(c, voices)
        made += bool(c.voice_id)
    return made


def run(ctx: Context) -> dict:
    cfg = ctx.cfg.characters
    if not cfg.enabled:
        ctx.log.info("character: 已禁用，跳过")
        return {"skipped": True}
    chars = list(ctx.project.characters)
    if not chars:
        ctx.log.warning("character: 还没有角色（先跑 analyze）")
        return {"characters": 0, "refs": 0}
    season = ctx.season
    season_done = bool(season and season.stage_status.get("character") == Status.DONE)
    anchors_ready = all(c.anchor_prompt or c.locked for c in chars)
    refs_ready = (not cfg.generate_refs) or all(
        _has_refs_on_disk(ctx, c) for c in chars)
    locs_ready = (not cfg.generate_location_refs) or all(
        any(ctx.store.abs(r).exists() for r in l.ref_images)
        for l in ctx.project.locations)
    cast_ready = (not cfg.auto_cast) or all(c.voice_id for c in chars)
    if season_done and anchors_ready and refs_ready and locs_ready and cast_ready:
        ctx.log.info("character: 第%d季已完成，跳过", ctx.season_index)
        return {"skipped": True, "season": ctx.season_index}

    ctx.check_stop()   # 一步一问：停止能在下一个动作生效
    anchors = build_anchors(ctx, chars)
    # the characters that would come out as copies are changed before the
    # pictures are made, not after.  A locked character is left alone: a
    # locked look is the user's decision, not the casting director's.
    ctx.check_stop()
    anchors += differentiate_characters(ctx, [c for c in chars if not c.locked])
    ctx.check_stop()
    casted = cast_voices(ctx, chars)
    # a sample of each voice, so the picture machine can start without
    # waiting for the voice machine to finish its lines
    voice_refs = generate_voice_refs(ctx, chars)
    refs = 0
    if cfg.generate_refs:
        refs = sum(generate_refs(ctx, c) for c in chars)
    loc_refs = generate_location_refs(ctx) if cfg.generate_location_refs else 0
    # this season's looks, written down for the seasons that follow
    record_season_looks(ctx, chars)
    ctx.save()
    ctx.project.stage_status["character"] = Status.DONE
    if season is not None:
        season.stage_status["character"] = Status.DONE
    ctx.save()
    ctx.log.info("character: 第%d季 %d 个角色，锚点补齐 %d，选角 %d，参考图 %d，"
                 "场景参考图 %d，声音样本 %d",
                 ctx.season_index, len(chars), anchors, casted, refs, loc_refs,
                 voice_refs)
    return {"characters": len(chars), "anchors": anchors, "cast": casted,
            "refs": refs, "location_refs": loc_refs, "season": ctx.season_index}


def generate_for_one(store: ProjectStore, cfg: Config, name: str,
                     views: list[str] | None = None) -> dict:
    """API entry: refresh one character's anchor and reference images."""
    ctx = Context(cfg, store)
    char = ctx.project.character(name)
    if char is None:
        return {"ok": False, "error": f"没有角色：{name}"}
    build_anchors(ctx, [char])
    refs = generate_refs(ctx, char, views) if cfg.characters.generate_refs else 0
    ctx.save()
    return {"ok": True, "name": char.name, "anchor_prompt": char.anchor_prompt,
            "refs": refs, "ref_images": char.refs(), "ref_sheet": char.ref_sheet}
