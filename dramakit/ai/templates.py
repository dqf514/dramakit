"""Requirement templates: the pre-baked choices behind the "extra requirements"
window. The user should never have to think from a blank box — every input the
system needs from a human is offered as one-click chips, and free-text is always
optional on top.

Three families:
  * GENRE_PRESETS  — whole-config starting points (题材 → 画风/节奏/配乐/时长)
  * REQUIREMENT_CHIPS — small composable tweaks the user can stack
  * INTENT_EXAMPLES — example one-line intents for the auto-config box

These are plain data. autoconfig.py feeds the selected ones to the LLM as
structured constraints; the web console renders them as chips.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# 题材预设：一键决定整体风格
# --------------------------------------------------------------------------- #
GENRE_PRESETS: list[dict] = [
    {
        "id": "urban_sweet", "label": "都市甜宠",
        "genre": "都市", "style": "写实电影感，柔光，暖色调",
        "pacing": "轻快", "audience": "女频",
        "bgm": "浪漫轻快", "episode_duration": 90,
        "art": {"genre": "都市", "style": "写实电影感", "era": "当代",
                "color_palette": "暖色柔光"},
        "hint": "现代都市背景，男女主情感线为主，画面干净明亮。",
    },
    {
        "id": "war_god", "label": "战神/赘婿逆袭",
        "genre": "战神", "style": "写实电影感，强对比，冷色调",
        "pacing": "极快，强反转", "audience": "男频",
        "bgm": "燃向史诗", "episode_duration": 75,
        "art": {"genre": "战神", "style": "写实电影感", "era": "当代",
                "color_palette": "冷色高对比"},
        "hint": "身份反转、打脸爽点密集，节奏快，每集结尾留钩子。",
    },
    {
        "id": "costume", "label": "古装权谋",
        "genre": "古装", "style": "国风工笔，电影质感",
        "pacing": "沉稳", "audience": "通用",
        "bgm": "古风弦乐", "episode_duration": 100,
        "art": {"genre": "古装", "style": "国风电影质感", "era": "古代",
                "color_palette": "古典雅致"},
        "hint": "古代宫廷/江湖，服饰场景考究，台词偏文雅。",
    },
    {
        "id": "xuanhuan", "label": "玄幻修仙",
        "genre": "玄幻", "style": "奇幻瑰丽，特效感",
        "pacing": "快", "audience": "男频",
        "bgm": "恢弘奇幻", "episode_duration": 90,
        "art": {"genre": "玄幻", "style": "奇幻瑰丽", "era": "架空",
                "color_palette": "高饱和奇幻"},
        "hint": "修炼体系、法术特效、异世界景观。",
    },
    {
        "id": "suspense", "label": "悬疑短剧",
        "genre": "悬疑", "style": "写实电影感，暗调，硬光",
        "pacing": "紧凑，多伏笔", "audience": "通用",
        "bgm": "紧张悬疑", "episode_duration": 85,
        "art": {"genre": "悬疑", "style": "写实电影感", "era": "当代",
                "color_palette": "暗调冷色"},
        "hint": "案件/谜题推进，气氛压抑，信息差制造悬念。",
    },
    {
        "id": "rebirth", "label": "重生复仇",
        "genre": "重生", "style": "写实电影感，冷暖对撞",
        "pacing": "极快", "audience": "女频",
        "bgm": "情绪张力", "episode_duration": 80,
        "art": {"genre": "重生", "style": "写实电影感", "era": "当代",
                "color_palette": "冷暖对撞"},
        "hint": "主角带记忆重来，复仇打脸，情绪浓烈。",
    },
]

# --------------------------------------------------------------------------- #
# 需求 chip：可叠加的细粒度偏好
# --------------------------------------------------------------------------- #
REQUIREMENT_CHIPS: dict[str, list[dict]] = {
    "画风": [
        {"id": "style_real", "label": "写实电影感", "set": {"art.style": "写实电影感"}},
        {"id": "style_anime", "label": "日系动漫", "set": {"art.style": "日系动漫风格"}},
        {"id": "style_cartoon", "label": "卡通风", "set": {"art.style": "卡通插画风"}},
        {"id": "style_guofeng", "label": "国风水墨", "set": {"art.style": "国风水墨"}},
        {"id": "style_cyber", "label": "赛博朋克", "set": {"art.style": "赛博朋克霓虹"}},
    ],
    "节奏": [
        {"id": "pace_fast", "label": "快节奏爽剧", "set": {"pacing": "极快", "segment.episode_duration": 70}},
        {"id": "pace_normal", "label": "标准节奏", "set": {"pacing": "标准", "segment.episode_duration": 90}},
        {"id": "pace_slow", "label": "慢热情感", "set": {"pacing": "舒缓", "segment.episode_duration": 120}},
    ],
    "受众": [
        {"id": "aud_female", "label": "女频", "set": {"audience": "女频"}},
        {"id": "aud_male", "label": "男频", "set": {"audience": "男频"}},
        {"id": "aud_all", "label": "全年龄", "set": {"audience": "通用"}},
    ],
    "时长/集": [
        {"id": "dur_60", "label": "~60秒", "set": {"segment.episode_duration": 60}},
        {"id": "dur_90", "label": "~90秒", "set": {"segment.episode_duration": 90}},
        {"id": "dur_120", "label": "~2分钟", "set": {"segment.episode_duration": 120}},
    ],
    "画面比例": [
        {"id": "ar_916", "label": "竖屏 9:16", "set": {"compose.width": 1080, "compose.height": 1920}},
        {"id": "ar_169", "label": "横屏 16:9", "set": {"compose.width": 1920, "compose.height": 1080}},
    ],
    "字幕": [
        {"id": "sub_on", "label": "烧录字幕", "set": {"compose.burn_subtitles": True}},
        {"id": "sub_off", "label": "不烧字幕", "set": {"compose.burn_subtitles": False}},
    ],
    "配音": [
        {"id": "tts_edge", "label": "Edge免费音色", "set": {"tts.provider": "edge"}},
        {"id": "tts_cosy", "label": "本地CosyVoice", "set": {"tts.provider": "cosyvoice"}},
    ],
    "配乐": [
        {"id": "bgm_lib", "label": "本地乐库", "set": {"music.provider": "library"}},
        {"id": "bgm_gen", "label": "AI生成配乐", "set": {"music.provider": "musicgen"}},
        {"id": "bgm_none", "label": "无配乐", "set": {"music.provider": "none"}},
    ],
}

# --------------------------------------------------------------------------- #
# 大模型 Provider 预设：设置页一键填入 base_url / 示例模型 / 是否需要 Key
# --------------------------------------------------------------------------- #
LLM_PROVIDERS: list[dict] = [
    {"id": "ollama", "label": "Ollama（本地）", "base_url": "http://localhost:11434/v1",
     "model": "qwen2.5:14b", "need_key": False, "api_key": "ollama",
     "hint": "本地免费；先 `ollama pull` 模型，服务默认 11434"},
    {"id": "lmstudio", "label": "LM Studio（本地）", "base_url": "http://localhost:1234/v1",
     "model": "", "need_key": False, "api_key": "lm-studio",
     "hint": "本地；需在 LM Studio 里开启 Developer Server"},
    {"id": "deepseek", "label": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
     "model": "deepseek-chat", "need_key": True, "api_key": "",
     "hint": "国内直连，性价比高"},
    {"id": "qwen", "label": "通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "model": "qwen-plus", "need_key": True, "api_key": "",
     "hint": "阿里云百炼 API Key"},
    {"id": "kimi", "label": "Kimi（月之暗面）", "base_url": "https://api.moonshot.cn/v1",
     "model": "moonshot-v1-32k", "need_key": True, "api_key": "",
     "hint": "长上下文，适合整本小说"},
    {"id": "openai", "label": "OpenAI", "base_url": "https://api.openai.com/v1",
     "model": "gpt-4o-mini", "need_key": True, "api_key": "",
     "hint": "海外接口；网络需代理时把 use_proxy 设为 true"},
    {"id": "zhipu", "label": "智谱 GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4",
     "model": "glm-4-flash", "need_key": True, "api_key": "",
     "hint": "bigmodel.cn 开放平台"},
    {"id": "custom", "label": "自定义 / 其它", "base_url": "", "model": "",
     "need_key": False, "api_key": "",
     "hint": "任意 OpenAI 兼容 /v1 接口（vLLM、llama.cpp、网关…）"},
]


# --------------------------------------------------------------------------- #
# 模型分工：设置页里每个模型勾选负责哪些任务
# --------------------------------------------------------------------------- #
MODEL_ROLES: list[dict] = [
    {"id": "analyze", "label": "小说分析", "desc": "提取人物、世界观、情节大纲"},
    {"id": "segment", "label": "智能分集", "desc": "切集、结尾钩子设计"},
    {"id": "script", "label": "剧本", "desc": "场景、台词、动作改写"},
    {"id": "storyboard", "label": "分镜", "desc": "镜头、景别、运镜设计"},
    {"id": "promptgen", "label": "画面提示词", "desc": "生图/视频提示词"},
    {"id": "config", "label": "一键配置", "desc": "一句话意图 → 全参数配置"},
    {"id": "actions", "label": "智能动作", "desc": "自然语言指令解析"},
    {"id": "search", "label": "语义检索", "desc": "查询扩展与筛选"},
    {"id": "tag", "label": "标签/摘要", "desc": "打标签、分类、摘要（高频小活）"},
]

MODEL_ROLE_IDS: list[str] = [r["id"] for r in MODEL_ROLES]

# --------------------------------------------------------------------------- #
# 意图示例：一键配置输入框的占位/快捷
# --------------------------------------------------------------------------- #
INTENT_EXAMPLES: list[str] = [
    "做一部都市甜宠短剧，女频，节奏轻快，写实电影感，竖屏",
    "男频战神逆袭，节奏极快，每集结尾强钩子，冷色调",
    "古装权谋，沉稳大气，国风画面，台词文雅",
    "悬疑短剧，暗调硬光，多伏笔，紧张配乐",
]


def preset_by_id(pid: str) -> dict | None:
    return next((p for p in GENRE_PRESETS if p["id"] == pid), None)


def apply_chip_ids(chip_ids: list[str]) -> dict:
    """Flatten selected chip ids into a {dotted.path: value} override map."""
    by_id = {}
    for group in REQUIREMENT_CHIPS.values():
        for c in group:
            by_id[c["id"]] = c
    out: dict = {}
    for cid in chip_ids or []:
        c = by_id.get(cid)
        if c:
            out.update(c["set"])
    return out


def all_templates() -> dict:
    """Everything the web console needs to render the requirement window."""
    return {
        "genre_presets": GENRE_PRESETS,
        "requirement_chips": REQUIREMENT_CHIPS,
        "intent_examples": INTENT_EXAMPLES,
        "llm_providers": LLM_PROVIDERS,
        "model_roles": MODEL_ROLES,
    }
