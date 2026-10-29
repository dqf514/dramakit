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
  - **visual_prompt 必须唯一**：每样东西只写一种——一种桌子材质、一个主色调、
    一种地板。写成 "wood and marble table" 的话，每一镜的画都会挑一种，
    桌子就在木纹和大理石之间跳。还要写死固定物体的位置：窗在左还是右、
    卡座在哪边、背景是什么，写清楚之后每一镜都照着来
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
VOICE_CAST_SYSTEM = """你是短剧配音导演。根据剧情、角色定位、性别、年龄、性格，为每个角色
设计一套专属声音（音色 + 音高/语速微调）。只输出JSON。

设计要点：
- voice_id 必须从给定音色表里选完整名称
- 同时给出该角色的音高/语速微调，用来区分年龄与身份：
    pitch: "-16Hz" 更低沉年长 / "+10Hz" 更年轻明亮 / "+0Hz" 不改
    rate:  "-10%" 更慢更沉稳 / "+8%" 更急更紧张 / "+0%" 不改
- 主角与女主：清晰有辨识度，不要过度加工
- 长辈：更低更慢；少年少女：更亮更快；反派：更低沉或更冷
- 同一剧里尽量不重复 voice_id；必须复用时用不同 pitch/rate 拉开差别
- 不要给"旁白"分配，旁白由系统单独处理"""

VOICE_CAST_USER = """为下面这些角色设计专属声音。

本剧设定：题材 {{genre}}；画风 {{style}}；年代 {{era}}
本剧情绪基调：{{tone}}

角色：
{{characters}}

可用音色（只能从中选，返回完整名称；注释是该音色气质）：
{{voices}}

要求：
- 男主/青年男性优先沉稳定型男声；女主/青年女性优先清晰有辨识度的女声；
  长辈选更沉稳的，反派可选偏低沉或阴冷的音色。
- 同一部剧里尽量不重复；角色较多时允许复用，但男女不能混用。
- 不要给"旁白"分配，旁白由系统单独处理。
- 每个角色都要给出 pitch 与 rate，让声音能听出年龄和身份差别。

输出JSON：
{"characters":[{"name":"","voice_id":"","pitch":"","rate":""}]}"""


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
- **台词要按"表演"写，不是按"文稿"写**（这条直接决定配音有没有感染力）：
  - 一句台词不超过 12 个字，情绪强的场景可以更短、可以只蹦一两个字
  - 台词念出来要快：一集念完不超过 {{budget_seconds}} 秒，句数不超过 {{budget_lines}} 句
  - 台词正文里带语气词和情绪词：犹豫用"你、你到底……"，压不住用"你少来这套"，
    崩溃用"我不信……我不信！"，狠话用"你以为你赢定了？"
  - 括号里的表演提示（咬牙/颤抖/哽咽/低吼）写进 emotion 字段，**不要写进 text**
    ——text 会被配音模型念出来，也会出现在字幕上
  - 台词里不要出现旁白式叙述、也不要写动作（动作交给画面）
- 对白优先推进冲突与反转，删除冗长描写；旁白精简
- **开头三秒就是钩子**（爆款短剧的第一条命门）：
  - 第一句台词必须是**冲突已经发生**的那一句——威胁、质问、揭穿、反常的一句话；
    不要用交代背景的句子开场（"三年前那件事你还记得吗"这类不行）
  - 第一个画面就要有信息量，不要用空镜慢开场
  - 前 3 秒必须有人开口
- **结尾必须翻盘**：
  - 最后一两句要有反转、揭穿或新的真相，让观众想看下一集
  - 钩子要落在台词上，不要用旁白交代"欲知后事如何"
- **信息量预算（短剧的第一原则：宁快勿拖）**：
  - 全集台词念出来大约 {{budget_seconds}} 秒，总字数不超过 {{budget_chars}} 字，句数不超过 {{budget_lines}} 句
  - 每集只确立一个核心情绪、一个信息增量；能砍的都砍掉
  - 旁白只留交代必要的时空/身份信息，一两句为限
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
- **景别必须有变化**：不要连着三个同景别。两个角色对话要用正反打（过肩 ↔ 特写交替），
  否则整集看起来像同一张证件照在播。每场第一个镜头用中景或全景交代环境，
  不要一上来就给特写（观众还不知道这是谁、在哪里）。
  **全集的第一个镜头要同时干两件事**：交代环境，并且画面里的人开口说钩子
  （中景，人物已经在说话），不要先来一个没人说话的空镜。
- **同一个角色连续独白不超过两个镜头**：第三个镜头要切给对方——不是对方的脸，
  就是对方在听时的反应（眼神、呼吸、手上的小动作）。一整段都是一个人在说，
  观众就只剩下"听说明书"的感觉。
- **结尾要把对方的反应拍出来**：最后一集不能停在一个人把话说完就结束，
  要么最后一句台词由对方说，要么最后留一个镜头给对方听到之后的反应
  （怔住、眼泪、攥紧的手、转身离开）——短剧的付费卡点就在这个反应上
- **台词里的关键名词要拍出来**：观众听到"车祸""护腿""合同""戒指""股份"这些词时，
  画面上就要有对应的东西——要么是一个插入特写（照片、病历、合同、戒指的特写），
  要么是这个道具在画面里清清楚楚。只用嘴说，观众就只在听说明书
- **道具的状态要连贯**：戒指、杯子、手机、文件这些道具在每一镜的状态必须接得上
  上一镜（桌上 → 被拿起来 → 放进盒子 → 重新戴上），中间不能凭空跳变；
  桌上固定的东西（杯子几个、文件在谁手边）也不要换
- **动作要跟着台词走**：镜头的动作描述必须和这一镜承载的台词对得上
  （说"三个月"就抬三根手指，说"我滚"就要真的转身往门口走），
  不要把一个动作写在不属于它的镜头里
- **机位也要有对比**：强势的一方可以略低机位（显得压人），弱势的一方略高机位，
  但每场最多用一次，不要跳。
- camera_move: 固定/推/拉/摇/移/跟（{{prefer_dynamic}}）
- duration: 该镜头秒数（{{dur_min}}~{{dur_max}}秒；对白镜头时长要够说完对应台词）
- action: 画面内容中文描述（谁、在哪、做什么、什么表情）
- characters: 出镜角色姓名数组（从这些里选：{{character_names}}）
- **lines: 该镜头覆盖的「对白」行号（上面台词列表里的编号，从1开始）**。这是最关键的一项：
  镜头要切在台词上，说话的人必须在画面里。一句对白只属于一个镜头，不要重复分配；
  每句对白都要有归属；旁白/字幕卡不算对白，填 []。
- **节奏：一个镜头承载的对白不超过 4.5 秒**：一句台词，或者两句短的
  （同一个说话人，中间要留出半秒的停顿——镜头不急着切，让观众听清楚）。
  换了说话人就切镜（正反打），观众才跟得上谁在说。
  **不要一句一镜**：连着几句台词可以留在同一个镜头里（对话戏的镜头常常停很久），
  但一句话说完之后要给对方一点反应的时间。连续两个超过 5 秒的镜头会让观众划走。
- 镜头时长之和应≈本场台词总时长({{narration_seconds}}秒)
{% if ref_rhythm %}
- **参考片的剪辑节奏（照着这个速度切）**：平均 {{ref_avg}} 秒一刀，中位 {{ref_median}} 秒，
  最长不超过 {{ref_max}} 秒，开场第一个镜头 {{ref_open}} 秒，每分钟约 {{ref_cpm}} 刀。
  本集的镜头要切得和它一样密。
{% endif %}

输出JSON：
{"shots":[{"shot_type":"近景","camera_move":"推","duration":3.0,"action":"","characters":[],"lines":[1,2]}]}"""


# --------------------------------------------------------------------------- #
# PROMPTGEN — image/video generation prompt per shot
# --------------------------------------------------------------------------- #
PROMPT_SYSTEM = """你是AI绘画提示词工程师，为短剧分镜写高质量的出图/出视频提示词。
只输出JSON。"""

PROMPT_USER = """为下面这个{{aspect}}镜头生成AI绘画提示词。

镜头：{{shot_type}} / 运镜 {{camera_move}}（本镜约 {{duration}} 秒）
画面：{{action}}
出镜角色及锁定锚点（必须原样沿用，外貌/发型/服装一个字都不要改写）：
{{character_anchors}}
场景：{{location}} / {{time_of_day}}
场景设定（保持一致，不要改建筑风格/陈设）：{{location_visual}}
（**场景参考图是唯一标准**：桌子的材质和颜色、窗户在哪边、座位怎么排、
背景里有什么，都照着参考图来，不要换、不要重新设计）
本场剧情：{{scene_summary}}
全剧画风：{{style}}；年代：{{era}}；色调：{{color_palette}}
镜头情绪：{{mood}}

规则：
- prompt: 英文提示词。结构必须是【角色锚点在前】+ 动作表情 + 环境 + 光线 + 镜头(shot type,角度)+ 画风 + 画质词；{{composition}}
- negative_prompt: 英文负面词，在全局负面基础上补充本镜头要避免的
- 若出镜多个角色，prompt中按姓名逐一描述外貌，避免混淆
{% if end_frame %}- end_prompt: 同一镜头最后一帧的英文提示词。只描述最终姿态/位置/表情，角色锚点、服装、场景和光线必须与 prompt 完全一致；不要新增角色，不要换装
{% endif %}
输出JSON：
{"prompt":"","negative_prompt":"","end_prompt":""}"""


# --------------------------------------------------------------------------- #
# PROMPTGEN — FLUX 3 Image Klein (full scene caption, not keyword soup)
#
# FLUX 3 does not read SDXL-style prompts. It takes one continuous scene
# caption (100-350 words) that a human would write for a still frame. A short
# keyword prompt produces a generic, interchangeable image - BFL's own docs
# say to never use the model without a prompt upsampler for this reason.
# The rules below are distilled from BFL's official upsampler system prompt.
# --------------------------------------------------------------------------- #
FLUX3_IMAGE_SYSTEM = """你是 FLUX 3 出图提示词导演。

FLUX 3 Image Klein 接收的是"一段完整场景描述"（full scene caption），不是关键词堆叠。
短提示词会得到泛化、平庸、可替换任何情节的画面。只输出JSON。

硬规则：
- prompt 必须是英文，一段连续散文，100~350 词，不要分行成条目
- 以媒介与风格开头：Full-color outdoor photograph, ... / Full-color indoor photograph, ... /
  Studio photograph, ... / Close-up photograph, ...
- 顺序：媒介与风格 → 场景 → 光线 → 镜头 → 人物（位置/外貌/服装/材质/状态）→ 前景与背景
- 用画面相对位置：frame-left / frame-right / upper / lower / foreground / midground / background
- 角色锚点必须原样沿用，一个字都不要改写；多角色时按姓名逐一描述，避免混淆
- **画面里只能有列出的人物**：不要凭空多出第四个人、不要在前景放来路不明的后脑勺或肩膀；
  背景里可以有虚化的人影，但不许清楚到能认出是谁
- 不要写画质套话：8k / masterpiece / best quality / ultra detailed / trending
- 不要写"This image shows"这类元叙述，不要以情绪或品质判断收尾
- 背景只占约六分之一；虚焦或远景只写形状、颜色、剪影，不编造身份，不编造可读文字
- **画面里不要出现任何文字**：字幕是后期加的，提示词里的引号台词不要当成画面里的字
  写进描述（那会让模型把台词当字幕烧进画面）。把台词改写成"谁在说什么表情"，
  引号里的原话不要出现在英文描述里
- negative_prompt 必须留空：FLUX 3 常规 checkpoint 不使用负向提示词
"""

FLUX3_IMAGE_USER = """为下面这个{{aspect}}镜头写一段 FLUX 3 完整场景描述。

镜头：{{shot_type}} / 运镜 {{camera_move}}
画面：{{action}}
出镜角色及锁定锚点（必须原样沿用，外貌/发型/服装一个字都不要改写）：
{{character_anchors}}
场景：{{location}} / {{time_of_day}}
场景设定（保持一致，不要改建筑风格/陈设）：{{location_visual}}
（**场景参考图是唯一标准**：桌子的材质和颜色、窗户在哪边、座位怎么排、
背景里有什么，都照着参考图来，不要换、不要重新设计）
本场剧情：{{scene_summary}}
全剧画风：{{style}}；年代：{{era}}；色调：{{color_palette}}
镜头情绪：{{mood}}
{% if continuity %}
上一镜结束时的状态（**必须接得上**：人物的站位、姿势、朝向、与环境的相对位置要连贯）：{{continuity}}
{% endif %}

要求：
- 开头用"Full-color outdoor photograph"这类摄影惯例短语承接全剧画风
- 人物在画面中的位置、姿态、视线、手上动作要具体可执行
{% if continuity %}
- 人物的站位和姿势要接上上一镜：上一镜他站着，这一镜就别突然坐下；反之亦然
{% endif %}
- 环境要给出该场景自己的具体物件，不要写成通用素材库
- 描述里不要提及画幅比例，"TARGET CANVAS" 之类的词也不要出现
{% if end_frame %}- end_prompt: 同一镜头最后一帧的完整场景描述。只改最终姿态/位置/表情，角色锚点、服装、场景和光线必须与 prompt 完全一致；不要新增角色，不要换装
{% endif %}
输出JSON：
{"prompt":"","negative_prompt":"","end_prompt":""}"""


# PROMPTGEN — MiniMax H3 official three-field video prompt (I2VA: first frame)
# Rules distilled from the official H3 prompt spec (keyframe / T2VA skill).
# --------------------------------------------------------------------------- #
H3_VIDEO_SYSTEM = """你是 MiniMax H3 视频提示词导演，按官方规范为单个镜头生成 H3 提示词。
只输出JSON。

官方三字段（必须齐全，顺序固定）：
integrated_multimodal_description / overall_soundscape / non_diegetic_music

硬规则：
- 所有描述性文字用英文书写；只有对白/歌词保留原文语言
- integrated_multimodal_description 以 "[Shot 1] " 开头；只写这一个镜头，不要写切镜
- 先写风格与初始构图，再写人物位置/服装/环境/光线，然后动作与运镜，最后对白
- 运镜用官方术语并融进自然英文散文，不要写成标签列表：
  Zoom In/Zoom Out=变焦(机身不动)；Push In/Pull Out=推拉(机身前后移)；
  Pan Left/Right=摇(固定机位水平转)；Truck Left/Right=移(机身水平平移)；
  Tilt Up/Down=俯仰(固定机位垂直转)；Pedestal Up/Down=升降(机身垂直移动)；
  Arc Shot=环绕；Tracking Shot=跟随；Static Shot=固定；POV=主观视角
- 对白原样写进 <d>[zh-CN]台词</d>；说话人标注 (S1)/(S2)，只给真正发声的角色，
  同一角色跨镜头复用同一编号；身份与说话动作写在 <d> 之外
- **当用户提示说明台词由后期配音轨提供时（bed 模式）：不要写 <d> 标签，
  但要描述角色说话时的表演（开口、语气），画面里才有对得上的口型；
  台词内容与配音由后期轨提供**
- overall_soundscape 用 1-4 句概括环境声、动作声、非语言人声，不要重复对白；
  bed 模式下只写环境声与动作声，不要有人的说话声
- non_diegetic_music 用 1-3 句描述观众听到的配乐：乐器、节奏速度、动态起伏；没有就给 N/A
- 不要写 negative prompt，不要出现 "no text"、"without watermark" 这类否定描述
- **integrated_multimodal_description 的结尾必须原样写上这些约束**（写在描述的最后）：
  保持人物身份、脸部、发型与服装和第一帧完全一致；画面里不出现除第一帧已有文字以外的新文字，
  也不加字幕和水印；不出现多余人物、多余肢体或畸形的手；镜头不抖动、不跳帧、不慢动作；
  不要切换到别的场景或别的机位；全片人脸的五官比例不变，脸不变长、不变窄、不变胖，
  眼睛和嘴的形状保持一致；人物动作幅度小，只做细微的表情、眼神和呼吸；
  镜头运动平缓，不要突然加速或甩动。
- **描述里要写清楚时间轴**（例如 "From 0.0 to 2.0 seconds, ..."），
  各段时间之和必须等于本镜时长；还要写明角色说话时的口型动作（opens her mouth and speaks），
  台词由后期配音轨提供，画面里的口型要对得上。
- **一个镜头里只有台词表里的说话人开口**：其余人嘴要闭着，只是听和反应，
  不张嘴、不出声；说话人的嘴型要跟后期配音轨对上
- 画面是 9:16 竖屏"""

H3_VIDEO_USER = """为下面这个镜头生成 MiniMax H3 提示词（I2VA 模式：图片是第一帧）。

镜头：{{shot_type}} / 运镜 {{camera_move}}
画面：{{action}}
出镜角色（外貌/发型/服装必须与给定描述完全一致，不要改写）：
{{character_anchors}}
场景：{{location}} / {{time_of_day}}
场景设定（保持一致）：{{location_visual}}
（场景参考图是唯一标准：桌子的材质和颜色、窗户位置、座位关系都不要变）
本场剧情：{{scene_summary}}
全剧画风：{{style}}；年代：{{era}}；色调：{{color_palette}}
镜头情绪：{{mood}}
本镜台词（speaker 已换成编号；没有台词就写"无"）：
{{dialogue}}
{% if continuity %}
上一镜结束时的状态（**必须接得上**：人物的站位、姿势、朝向、与环境的相对位置要连贯）：{{continuity}}
{% endif %}
{{dialogue_note}}

**参考图的分工**：
{{references}}

**时间轴（必须与 {{duration}} 秒一致）**：
{{timeline}}

要求：
- integrated_multimodal_description 以 [Shot 1] 开头，描述这一镜的完整画面与运动
- 本镜台词用 <d>[zh-CN]...</d> 包住，保留原样台词
- **integrated_multimodal_description 的最后要原样带上这些约束**（写在描述的结尾）：
  {{constraints}}
输出JSON：
{"integrated_multimodal_description":"","overall_soundscape":"","non_diegetic_music":""}"""


H3_SCORE_SYSTEM = """你是短剧配乐导演，为一个**没有人、没有角色、没有对白**的空镜写 H3 提示词。
只输出JSON。

官方三字段（必须齐全）：integrated_multimodal_description / overall_soundscape / non_diegetic_music

硬规则：
- 所有描述性文字用英文书写
- integrated_multimodal_description 以 "[Shot 1] " 开头：只写这个空镜头的环境、天气、光线与缓慢的镜头运动
- 必须写明 no people, no characters, no voices
- overall_soundscape 只写环境声（雨、风、街道、车辆、机器、室内空气），不要有任何人的声音
- non_diegetic_music 写这一场该有的配乐：乐器、速度、情绪走向；短剧要的是情绪张力，不是电影感
- 不要写 negative prompt，不要出现否定描述"""

H3_SCORE_USER = """为下面这个场景生成一段**纯配乐镜头**的 H3 提示词。

场景：{{location}} / {{time_of_day}}
场景设定：{{location_visual}}
本场情绪：{{mood}}
本场剧情：{{scene_summary}}
关键动作（这些动作的声音要出现在配乐镜头里）：{{scene_actions}}
全剧画风：{{style}}

这个镜头里**没有任何人、没有角色、没有对白**，只有环境声、动作声与配乐：
- integrated_multimodal_description 以 [Shot 1] 开头：写这个空镜头的画面（环境、天气、光线、镜头缓慢移动），明确写明 no people, no characters, no voices
- overall_soundscape：写环境声（雨、风、街道、车辆、机器、室内空气）**以及本场关键动作的声音**（门响、电话铃、脚步、器物碰撞等，最多三个），**不要有任何人的说话声**
- non_diegetic_music：写这一场该有的配乐（乐器、速度、情绪走向）

输出JSON：
{"integrated_multimodal_description":"","overall_soundscape":"","non_diegetic_music":""}"""


def render(template: str, **ctx) -> str:
    return _env.from_string(template).render(**ctx)
