"""Jinja2 prompt templates for every LLM stage.

All templates demand STRICT JSON output so we can parse deterministically. They
are written for Chinese vertical short-drama (红果/抖音短剧) conventions: fast
cold-open conflict, a hook at every episode end, tight dialogue, and shot types
that read well on a phone in 9:16.
"""
from __future__ import annotations

from jinja2 import Environment, StrictUndefined

_env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)


# --------------------------------------------------------------------------- #
# ANALYZE — characters / world / art direction
# --------------------------------------------------------------------------- #
ANALYZE_SYSTEM = """你是资深短剧编剧与美术指导。阅读小说/剧本，抽取用于AI短剧制作的设定。
只输出JSON，不要解释。"""

ANALYZE_USER = """请从下面文本中抽取短剧设定。

要求：
- title: 剧名（若无则自拟一个吸引人的短剧名）
- genre: 题材（如 都市/古装/战神/甜宠/复仇/穿越/悬疑）
- synopsis: 50字以内一句话故事梗概
- characters: 主要角色（最多{{max_characters}}个，按戏份排序）
  - name 姓名; aliases 别称数组; role 定位(男主/女主/反派/配角等);
    gender 性别(男/女/未知); age 年龄; personality 性格;
    appearance 外貌(发型/五官/身材/标志性特征，中文);
    visual_prompt 用于AI出图的英文外貌描述(稳定、可复用，含发型服装气质)
- locations: 主要场景（最多{{max_locations}}个）: name, description, visual_prompt(英文)
- art_direction: style 画风, era 年代, color_palette 色调

文本：
\"\"\"
{{text}}
\"\"\"

输出JSON格式：
{
  "title": "", "genre": "", "synopsis": "",
  "characters": [{"name":"","aliases":[],"role":"","gender":"","age":"","personality":"","appearance":"","visual_prompt":""}],
  "locations": [{"name":"","description":"","visual_prompt":""}],
  "art_direction": {"style":"","era":"","color_palette":""}
}"""


# --------------------------------------------------------------------------- #
# CHARACTER — 角色定妆锚点（跨镜头一致性的核心）
# --------------------------------------------------------------------------- #
CHARACTER_SHEET_SYSTEM = """你是短剧角色定妆师。把角色设定整理成可复用的英文出图锚点。
只输出JSON。"""

CHARACTER_SHEET_USER = """为下面这些角色生成"角色锁定锚点"。锚点会原样拼进每个镜头的出图提示词，
所以必须稳定、具体、只描述人本身，不要包含动作、镜头、场景或情绪。

角色：
{{characters}}

要求：
- anchor_prompt: 英文，按固定顺序描述：年龄段/性别/族裔 → 脸型五官 → 发型发色 → 固定服装 → 标志性配饰/特征。
  不使用 "beautiful/handsome" 这类空泛词；不使用会随镜头变化的动作或表情。
  长度不超过 {{max_chars}} 字符。
- negative_prompt: 该角色需要避免的英文负面词（如 age drift, different hairstyle, changing outfit），可为空。
- 已被用户锁定的角色不要改写（下面标记 locked 的保持原样）。

输出JSON：
{"characters":[{"name":"","anchor_prompt":"","negative_prompt":""}]}"""


# --------------------------------------------------------------------------- #
# VOICE CAST — assign a TTS voice to every character
# --------------------------------------------------------------------------- #
VOICE_CAST_SYSTEM = """你是短剧配音导演。根据角色性别、年龄、性格和定位，从给定音色表里
为每个角色挑最合适的一个。只输出JSON。"""

VOICE_CAST_USER = """为下面这些角色分配配音音色。

角色：
{{characters}}

可用音色（只能从中选，返回完整名称）：
{{voices}}

要求：
- 男主/青年男性优先沉稳定型男声；女主/青年女性优先清晰有辨识度的女声；
  长辈选更沉稳的，反派可选偏低沉或阴冷的音色。
- 同一部剧里尽量不重复；角色较多时允许复用，但男女不能混用。
- 不要给"旁白"分配，旁白由系统单独处理。

输出JSON：
{"characters":[{"name":"","voice_id":""}]}"""


# --------------------------------------------------------------------------- #
# SEGMENT — per-episode title / logline / hook
# --------------------------------------------------------------------------- #
SEGMENT_SYSTEM = """你是短剧分集策划。为每一集设计标题、一句话剧情和结尾钩子。
只输出JSON。"""

SEGMENT_USER = """这是短剧《{{title}}》的第 {{ep_index}} 集（共 {{ep_total}} 集）的原文片段。
目标时长约 {{duration}} 秒。请提炼本集信息。

钩子风格：{{hook_style}}。{{extra_hint}}

要求：
- title: 本集标题（6~14字，有张力）
- logline: 一句话剧情（30字内）
- hook: 本集结尾的悬念/反转钩子（一句，让人想看下一集）
- recap: 若{{ep_index}}>1，给一句"前情提要"，否则空字符串
- key_beats: 本集3~6个关键情节点（每个10字内）

原文片段：
\"\"\"
{{text}}
\"\"\"

输出JSON：
{"title":"","logline":"","hook":"","recap":"","key_beats":["","",""]}"""


# --------------------------------------------------------------------------- #
# SCRIPT — scene & dialogue breakdown
# --------------------------------------------------------------------------- #
SCRIPT_SYSTEM = """你是短剧编剧，把小说改编成可拍摄的短剧剧本。
只输出JSON。"""

SCRIPT_USER = """把下面这一集原文改编成短剧剧本。题材：{{genre}}。

改编规则：
- 拆成若干"场"（scene），同一时空为一场，一般{{min_scenes}}~{{max_scenes}}场
- 每场包含台词(lines)：
  - kind: dialogue(对白) / narration(旁白解说) / monologue(内心独白) / caption(字幕卡,如"三年后")
  - speaker: 说话人姓名；旁白用"旁白"
  - text: 台词内容，口语化、短促、有冲突感；旁白用于交代必要信息
  - emotion: 情绪(平静/愤怒/悲伤/惊讶/喜悦/紧张/得意等)
- 对白优先推进冲突与反转，删除冗长描写；旁白精简
- location/time_of_day(日/夜/晨/昏)/summary(一句话)/mood(氛围,用于配乐:紧张/悲伤/欢快/恢弘/浪漫/平静等)
- 只使用这些已确定角色（不要凭空新增主要角色）：{{character_names}}

原文：
\"\"\"
{{text}}
\"\"\"

输出JSON：
{"scenes":[{"location":"","time_of_day":"日","summary":"","mood":"","lines":[{"kind":"dialogue","speaker":"","text":"","emotion":"平静"}]}]}"""


# --------------------------------------------------------------------------- #
# STORYBOARD — shot list per scene
# --------------------------------------------------------------------------- #
STORYBOARD_SYSTEM = """你是短剧分镜师，为每场戏设计竖屏(9:16)分镜。
只输出JSON。"""

STORYBOARD_USER = """为下面这场戏设计分镜（竖屏手机观看）。

场景：{{location}} / {{time_of_day}} / 氛围 {{mood}}
剧情：{{summary}}
本场台词：
{{lines_text}}

分镜规则：
- 生成 {{min_shots}}~{{max_shots}} 个镜头，覆盖本场全部台词与动作
- shot_type: 特写/近景/中景/全景/远景/过肩/主观/空镜（对白多用近景特写，情绪爆发用特写，交代环境用全景/空镜）
- camera_move: 固定/推/拉/摇/移/跟（{{prefer_dynamic}}）
- duration: 该镜头秒数（{{dur_min}}~{{dur_max}}秒；对白镜头时长要够说完对应台词）
- action: 画面内容中文描述（谁、在哪、做什么、什么表情）
- characters: 出镜角色姓名数组（从这些里选：{{character_names}}）
- 镜头时长之和应≈本场台词总时长({{narration_seconds}}秒)

输出JSON：
{"shots":[{"shot_type":"近景","camera_move":"推","duration":3.0,"action":"","characters":[]}]}"""


# --------------------------------------------------------------------------- #
# PROMPTGEN — image/video generation prompt per shot
# --------------------------------------------------------------------------- #
PROMPT_SYSTEM = """你是AI绘画提示词工程师，为短剧分镜写高质量的出图/出视频提示词。
只输出JSON。"""

PROMPT_USER = """为下面这个竖屏(9:16)镜头生成AI绘画提示词。

镜头：{{shot_type}} / 运镜 {{camera_move}}
画面：{{action}}
出镜角色及锁定锚点（必须原样沿用，外貌/发型/服装一个字都不要改写）：
{{character_anchors}}
场景：{{location}} / {{time_of_day}}
场景设定（保持一致，不要改建筑风格/陈设）：{{location_visual}}
本场剧情：{{scene_summary}}
全剧画风：{{style}}；年代：{{era}}；色调：{{color_palette}}
镜头情绪：{{mood}}

规则：
- prompt: 英文提示词。结构必须是【角色锚点在前】+ 动作表情 + 环境 + 光线 + 镜头(shot type,角度)+ 画风 + 画质词；竖屏构图 vertical composition, 9:16
- negative_prompt: 英文负面词，在全局负面基础上补充本镜头要避免的
- 若出镜多个角色，prompt中按姓名逐一描述外貌，避免混淆
{% if end_frame %}- end_prompt: 同一镜头最后一帧的英文提示词。只描述最终姿态/位置/表情，角色锚点、服装、场景和光线必须与 prompt 完全一致；不要新增角色，不要换装
{% endif %}
输出JSON：
{"prompt":"","negative_prompt":"","end_prompt":""}"""


def render(template: str, **ctx) -> str:
    return _env.from_string(template).render(**ctx)
