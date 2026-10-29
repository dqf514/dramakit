"""Full parameter surface of DramaKit.

Everything is grouped into sections so config/default.yaml reads like a control
panel. Every AI capability is provider-agnostic: pick a `provider` and fill the
matching block. Cloud API and local deployment (Ollama / LMStudio / CosyVoice /
ComfyUI / MusicGen) are first-class and interchangeable.

Secrets (api_key) are read from the environment first, then from YAML, so you
can keep keys out of the config file:  e.g.  env  DRAMAKIT_LLM__API_KEY.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _drop_nulls(obj):
    """Recursively remove dict keys whose value is None, so commented-out YAML
    sections fall back to model defaults instead of failing validation."""
    if isinstance(obj, dict):
        return {k: _drop_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_drop_nulls(v) for v in obj]
    return obj


# --------------------------------------------------------------------------- #
# LLM
# --------------------------------------------------------------------------- #
class LLMConfig(BaseModel):
    # openai_compat covers: OpenAI, DeepSeek, Qwen/DashScope, Kimi, Groq,
    # Ollama (/v1), LM Studio (/v1), vLLM, llama.cpp server ...
    provider: Literal["openai_compat"] = "openai_compat"
    base_url: str = "http://localhost:11434/v1"       # Ollama default
    api_key: str = Field(default_factory=lambda: _env("DRAMAKIT_LLM_API_KEY", "ollama"))
    model: str = "qwen2.5:14b"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    timeout: float = 300.0
    max_retries: int = 3
    concurrency: int = 2                              # parallel LLM calls
    use_proxy: bool = False                           # 直连(False)；需经系统代理访问海外API时设 True
    # Per-stage model overrides (use a bigger model for segmentation, etc.)
    model_overrides: dict[str, str] = Field(default_factory=dict)
    json_mode: bool = True                            # request structured output
    system_prompt_extra: str = ""


# --------------------------------------------------------------------------- #
# 模型清单（多模型 + 任务分工 + 优先级 + 默认兜底）
# --------------------------------------------------------------------------- #
class ModelEntry(BaseModel):
    """One model in the registry.

    Entry order inside ModelsConfig.entries IS the priority order. `roles` are
    the task ids this model handles; every task nobody claims falls back to the
    entry marked as ModelsConfig.default.
    """
    id: str = ""
    label: str = ""                                   # 显示名，如「本地 Qwen」
    base_url: str = "http://localhost:11434/v1"
    api_key: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 300.0
    use_proxy: bool = False
    roles: list[str] = Field(default_factory=list)

    def to_llm(self, base: LLMConfig) -> LLMConfig:
        """Materialise a full LLMConfig for this entry, inheriting global
        knobs (top_p, json_mode, concurrency, ...) from `base`."""
        return base.model_copy(update={
            "base_url": self.base_url or base.base_url,
            "api_key": self.api_key,
            "model": self.model or base.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "use_proxy": self.use_proxy,
        })


class ModelsConfig(BaseModel):
    default: str = ""                                 # entry id used as fallback
    entries: list[ModelEntry] = Field(default_factory=list)

    def pick(self, role: str = "") -> Optional[ModelEntry]:
        """First entry (by priority) that claims `role`; else default; else #1."""
        if not self.entries:
            return None
        if role:
            for e in self.entries:
                if role in e.roles:
                    return e
        if self.default:
            for e in self.entries:
                if e.id == self.default:
                    return e
        return self.entries[0]


# --------------------------------------------------------------------------- #
# AI 大脑（行为开关 + 旧版 light_* 兼容；模型清单见 ModelsConfig）
# --------------------------------------------------------------------------- #
class AIConfig(BaseModel):
    """Controls the AI-native layer: auto-config, tagging, NL search, NL actions.

    Models themselves live in `Config.models`. The legacy `light_*` fields below
    are only used when the model registry is empty, so an older YAML keeps
    working with a single main LLM plus an optional small tagging model.
    """
    enabled: bool = True
    language: str = "zh"                              # AI 输出/标签语言
    main_timeout: float = 90.0                        # 交互式调用的超时上限(秒)
    # --- 旧版小模型（打标签/分类）；模型清单为空时才生效 ---
    light_base_url: str = ""                          # 例如 http://localhost:11434/v1
    light_api_key: str = Field(default_factory=lambda: _env("DRAMAKIT_AI_LIGHT_API_KEY", ""))
    light_model: str = ""                             # 例如 qwen2.5:3b
    light_temperature: float = 0.2
    light_max_tokens: int = 1024
    light_timeout: float = 120.0
    light_use_proxy: bool = False
    # --- 行为开关 ---
    auto_tag: bool = True                             # 流水线产出后自动打标签入库
    intent_confirm: bool = True                       # 自然语言动作执行前需确认
    catalog_db: str = "catalog.db"                    # 相对项目根或绝对路径
    max_search_results: int = 60
    tag_max: int = 8                                  # 每个资产最多标签数
    # 内置标签分类体系（AI 打标签时受此约束，保证分类清晰统一）
    tag_taxonomies: dict = Field(default_factory=lambda: {
        "genre": ["都市", "古装", "玄幻", "悬疑", "甜宠", "战神", "重生", "穿越", "复仇"],
        "scene_type": ["对白", "独白", "旁白", "打斗", "情感", "反转", "回忆", "空镜"],
        "mood": ["紧张", "温馨", "悲伤", "愤怒", "喜悦", "悬疑", "燃", "虐"],
        "shot": ["特写", "近景", "中景", "全景", "远景", "过肩", "主观", "空镜"],
        "time": ["日", "夜", "晨", "昏"],
        "asset": ["小说", "剧本", "分镜", "画面", "视频", "配音", "字幕", "配乐", "成片", "封面"],
    })


# --------------------------------------------------------------------------- #
# Web 控制台
# --------------------------------------------------------------------------- #
class WebConfig(BaseModel):
    host: str = "127.0.0.1"                           # 仅本机；局域网访问填 0.0.0.0
    port: int = 8756
    open_browser: bool = True
    projects_dir: str = "projects"
    title: str = "DramaKit 控制台"


# --------------------------------------------------------------------------- #
# 角色定妆 / 一致性
# --------------------------------------------------------------------------- #
class CharacterConfig(BaseModel):
    """角色锁定：稳定锚点 + 三视图参考图，跨镜头/跨集保持同一张脸。"""
    enabled: bool = True
    use_llm_anchor: bool = True                       # 用 LLM 把外貌整理成稳定英文锚点
    anchor_max_chars: int = 320
    generate_refs: bool = True                        # 用 ComfyUI 生成三视图
    generate_location_refs: bool = True               # 自动为每个场景出参考图
    auto_cast: bool = True                            # 自动给角色分配 TTS 音色
    # 正面、侧面、四分之三、背面：一张资产图上拼起来，人物全程不变
    ref_views: list[str] = Field(
        default_factory=lambda: ["front", "side", "three_quarter", "back"])
    ref_width: int = 768
    ref_height: int = 1024
    # prompt = 只靠文字锚点；ref = 出图时附带角色/场景参考图（需工作流支持）
    consistency: Literal["prompt", "ref", "lora"] = "ref"


# --------------------------------------------------------------------------- #
# TTS
# --------------------------------------------------------------------------- #
class TTSConfig(BaseModel):
    provider: Literal["edge", "cosyvoice", "openai", "minimax", "custom"] = "edge"
    # --- edge (free) ---
    edge_default_voice: str = "zh-CN-YunxiNeural"     # 男
    edge_narrator_voice: str = "zh-CN-YunyangNeural"  # 旁白/解说
    edge_female_voice: str = "zh-CN-XiaoxiaoNeural"   # 女
    # --- generic OpenAI-compatible /tts (also many local servers) ---
    base_url: str = "http://localhost:9880"           # CosyVoice HTTP default
    api_key: str = Field(default_factory=lambda: _env("DRAMAKIT_TTS_API_KEY", ""))
    model: str = "cosyvoice-v1"
    # --- shared voice shaping ---
    rate: str = "+0%"                                 # edge rate, e.g. +10%
    volume: str = "+0%"
    pitch: str = "+0Hz"
    speed: float = 1.0                                # non-edge providers
    concurrency: int = 4
    use_proxy: bool = False                           # 直连(False)；本地 CosyVoice 必须 False
    # character name -> voice id; unresolved characters fall back by gender
    voice_map: dict[str, str] = Field(default_factory=dict)
    # 旁白专用音色（非 edge 时用）
    narrator_voice: str = ""
    # 旁白/解说是否朗读。False = 只做屏幕文字（独有样式），不进入配音轨
    speak_narration: bool = False
    # --- 音色池筛选 ---
    # 只保留这些语言前缀的音色。默认纯普通话，避免粤语/台湾腔/方言混进短剧
    voice_locales: list[str] = Field(default_factory=lambda: ["zh-CN"])
    # 可选：显式音色白名单（留空 = 按 voice_locales 过滤）
    voice_pool: list[str] = Field(default_factory=list)
    # 可选：额外排除的音色
    voice_exclude: list[str] = Field(default_factory=list)
    # 音色 → 备注（喂给配音导演 LLM，说明年龄/气质）
    voice_notes: dict[str, str] = Field(default_factory=dict)
    # 情绪 -> provider 的情感参数。默认给的是 MiniMax 的英文枚举
    # （happy/sad/angry/fearful/disgusted/surprised/neutral）。
    # edge-tts 没有情感参数，会退回到上面的 emotion_modulation 做语速/音高微调。
    emotion_map: dict[str, str] = Field(default_factory=lambda: {
        "平静": "neutral", "愤怒": "angry", "悲伤": "sad",
        "惊讶": "surprised", "喜悦": "happy", "紧张": "fearful",
        "得意": "happy", "坚定": "neutral", "恐惧": "fearful",
        "厌恶": "disgusted", "疑惑": "surprised", "冷漠": "neutral",
    })
    # 情绪 -> 语速/音高微调。短剧要的是"戏感"：愤怒要顶上去，委屈要弱下来。
    # MiniMax 有真正的 emotion 参数，这张表是给没有情感能力的 TTS（edge）用的兜底。
    emotion_modulation: dict[str, dict] = Field(default_factory=lambda: {
        "愤怒": {"speed": 1.12, "pitch": -1},
        "悲伤": {"speed": 0.90, "pitch": -1},
        "惊讶": {"speed": 1.08, "pitch": 1},
        "喜悦": {"speed": 1.06, "pitch": 1},
        "紧张": {"speed": 1.10, "pitch": 0},
        "得意": {"speed": 0.98, "pitch": 0},
        "坚定": {"speed": 0.95, "pitch": -1},
        "恐惧": {"speed": 1.05, "pitch": 1},
        "厌恶": {"speed": 0.95, "pitch": -1},
    })
    # 情绪映射的默认值（中文情绪 -> MiniMax 的英文枚举）。
    # 留空则用这张内置表；provider 不支持情感时忽略即可。
    silence_pad_ms: int = 120                         # tail silence per line


# --------------------------------------------------------------------------- #
# ComfyUI (image + video generation)
# --------------------------------------------------------------------------- #
class NodeConfig(BaseModel):
    """One ComfyUI server in the fleet (the local one or an extra machine)."""
    name: str = "node"
    base_url: str = "http://127.0.0.1:8188"
    enabled: bool = True
    # What this node is for: "t2i" (stills), "i2v" (video). Empty = any task.
    # Specialising a node keeps one model resident instead of swapping between
    # two, which is where most of the per-shot time went.
    roles: list[str] = Field(default_factory=list)
    # --- how to ship model files to this node ---
    #   shared - the node's models dir is mounted here; copy into it
    #   scp    - copy over ssh to remote_models
    transfer: Literal["none", "shared", "scp"] = "none"
    ssh_host: str = ""
    ssh_user: str = ""
    ssh_key: str = ""                            # e.g. ~/.ssh/id_ed25519
    remote_models: str = ""                      # remote ComfyUI models dir (scp)
    local_models: str = ""                       # mounted remote models dir (shared)
    # --- auth ---
    auth: Literal["none", "basic", "bearer"] = "none"
    auth_username: str = ""
    auth_password: str = ""
    auth_token: str = ""
    extra_headers: dict = Field(default_factory=dict)
    verify_tls: bool = True
    # This node's own weights: {"6": {"unet_name": "..."}} - the loader
    # nodes of the workflow. The 5080 takes the nvfp4 files, the 3090 the
    # int8/convrot ones.
    graph_overrides: dict = Field(default_factory=dict)


class ComfyUIConfig(BaseModel):
    enabled: bool = True
    base_url: str = "http://127.0.0.1:8188"           # 远程机器填 http://<IP>:8188
    client_id: str = "dramakit"
    timeout: float = 600.0                            # 单张图/单段视频生成上限
    request_timeout: float = 60.0                     # 短HTTP调用(提交/查询/下载)超时
    poll_interval: float = 1.0
    concurrency: int = 1                              # 出图并发（本机一张卡，一次一个）
    video_concurrency: int = 2                        # 出视频并发（每个远端节点一个）                              # GPU-bound; keep low
    max_retries: int = 3                              # 远程网络抖动重试次数
    # --- 远程鉴权（对接另一台机器 + Nginx 反代时常用）---
    auth: Literal["none", "basic", "token", "header"] = "none"
    auth_username: str = ""                           # basic
    auth_password: str = Field(default_factory=lambda: _env("DRAMAKIT_COMFYUI_PASSWORD", ""))
    auth_token: str = Field(default_factory=lambda: _env("DRAMAKIT_COMFYUI_TOKEN", ""))  # bearer
    extra_headers: dict = Field(default_factory=dict)  # 任意自定义头（auth=header 或附加头）
    verify_tls: bool = True                           # 自签名证书的内网可设 false
    # --- 进度监听：优先 WebSocket，失败自动回退轮询 /history ---
    use_websocket: bool = True
    ws_fallback_to_poll: bool = True
    # 直连(False)，绕过 Windows 系统代理——局域网/远程 ComfyUI 必须 False；
    # 仅当经代理访问公网 ComfyUI 时才设 True
    use_proxy: bool = False
    # workflow templates (JSON exported from ComfyUI "API format")
    t2i_workflow: str = "config/comfyui/t2i_sdxl.json"
    # 带参考图的出图工作流（FLUX 3 的多参考图版）。有参考图时用它，
    # 没有时用上面的普通版 —— 多参考图版在无参考时会退化成正方形空潜空间。
    t2i_workflow_ref: str = ""
    i2v_workflow: str = "config/comfyui/i2v_animatediff.json"
    upscale_workflow: str = ""                        # optional
    auto_workflows: bool = True                       # missing file -> scan config/comfyui/
    auto_map: bool = True                             # infer node ids from the graph
    # 首尾帧：用 start+end 两张关键帧驱动 i2v（需支持双图的模型/工作流）
    first_last_frame: bool = False
    flf_workflow: str = ""                            # 双图 i2v 工作流；留空则退回单图
    # 模型文件名。FLUX / FLUX 3 这类"扩散模型 + 文本编码器 + VAE"三件套的架构，
    # checkpoint 写 UNETLoader 的 unet_name，clip/vae 各写自己的加载节点。
    clip_name: str = ""                               # CLIPLoader 的 clip_name
    vae_name: str = ""                                # VAELoader 的 vae_name
    # 出图提示词格式：sdxl = 关键词堆叠；flux3 = 完整场景描述（FLUX 3 Image Klein）
    prompt_format: Literal["sdxl", "flux3"] = "sdxl"
    # 出视频分辨率（H3 原生 16:9 是 1344x768，必须是 32 的倍数）。
    # 留空则用工作流里写死的值。
    video_width: int = 0
    video_height: int = 0
    # node id overrides inside the workflow to inject prompts/seed/size
    t2i_nodes: dict = Field(default_factory=lambda: {        "positive": "6", "negative": "7", "seed": "3",
        "width": "5", "height": "5", "steps": "3", "cfg": "3",
        "checkpoint": "4", "sampler": "3",
        "ref_image": "",                              # 可选：角色参考图 LoadImage 节点
    })
    # 让 H3 自己说话：画面、嘴型、人声、音效一次出。
    # 这条路只有 ref2va 模型走得通——fl2va 生成的人声是乱码。
    native_audio: bool = False
    # 每个视频都带上参考图（角色资产图、场景图、本镜首帧），参考图不齐就不抽卡
    video_references: bool = True
    ref_audio_node: str = "900"          # 工作流里装载参考音频的节点
    i2v_nodes: dict = Field(default_factory=lambda: {
        "image": "10", "positive": "6", "negative": "7",
        "seed": "3", "frames": "14", "fps": "15",
        "last_image": "",                             # 可选：尾帧 LoadImage 节点
    })
    # 节点池：额外的 ComfyUI 机器（方案B 的调度对象）。本地主节点不在此列。
    # 每个节点都需要工作流里引用的模型文件，可用 `dj nodes sync` 自动补齐。
    nodes: list[NodeConfig] = Field(default_factory=list)
    # What the local machine is for: [] = anything, ["t2i"] = only the stills
    local_roles: list[str] = Field(default_factory=list)
    # This machine's own weights for the loader nodes of the workflow
    graph_overrides: dict = Field(default_factory=dict)
    # 本机 ComfyUI 的 models 目录（模型文件的存放处，也是同步时的来源）。
    # 留空则默认用项目根目录下的 models/。
    models_dir: str = ""
    # generation defaults
    mode: Literal["image", "video", "image_then_video"] = "image_then_video"
    width: int = 768
    height: int = 1344                                # ~9:16
    steps: int = 25
    cfg: float = 6.5
    sampler: str = "dpmpp_2m"
    scheduler: str = "karras"
    checkpoint: str = "sd_xl_base_1.0.safetensors"
    frames: int = 32                                  # video frames per shot
    # 视频时长怎么定：
    #   auto  - 按每个镜头在时间线上实际占多长来生成（对齐 H3 的 17k+5 网格）
    #   fixed - 所有镜头都用上面的固定帧数
    # auto 让长镜头有足够内容，不用循环播放；短镜头也不会白白多生成。
    frame_mode: Literal["auto", "fixed"] = "auto"
    max_video_seconds: float = 15.0                   # 单镜头最长多少秒（H3 训练范围到 362 帧）
    fps: int = 16
    seed_mode: Literal["random", "fixed", "character"] = "character"
    fixed_seed: int = 12345
    save_intermediate: bool = True


# --------------------------------------------------------------------------- #
# Music / BGM
# --------------------------------------------------------------------------- #
class MusicConfig(BaseModel):
    provider: Literal["library", "musicgen", "suno", "none"] = "library"
    library_dir: str = "assets/music"
    # mood tag -> list of filenames (matched against scene.bgm_mood)
    mood_map: dict[str, list[str]] = Field(default_factory=dict)
    # musicgen (local, needs torch)
    base_url: str = "http://localhost:8001"
    model: str = "facebook/musicgen-small"
    duration: float = 30.0
    api_key: str = Field(default_factory=lambda: _env("DRAMAKIT_MUSIC_API_KEY", ""))
    use_proxy: bool = False                           # 直连(False)；本地 MusicGen 必须 False
    # mixing
    bgm_volume: float = 0.22                          # relative to voice
    loop_to_fit: bool = True
    fade_in: float = 1.0
    fade_out: float = 2.0
    duck_voice: bool = True                           # sidechain BGM under dialogue


# --------------------------------------------------------------------------- #
# Segmentation
# --------------------------------------------------------------------------- #
class SegmentConfig(BaseModel):
    strategy: Literal["auto", "fixed_count", "fixed_duration", "by_chapter"] = "auto"
    episode_count: int = 0                            # for fixed_count
    episode_duration: float = 300.0                   # 一集的目标时长（5 分钟）
    min_episode_duration: float = 180.0
    max_episode_duration: float = 360.0
    # a short drama episode is a minute: the script is written to this budget
    # however long the source text would take to read
    max_episode_seconds: float = 330.0
    respect_chapters: bool = True                     # align cuts to 章节 when possible
    hook_style: str = "强悬念反转"                     # 每集结尾钩子风格
    max_chars_per_episode: int = 0                    # 0 = let LLM decide by duration
    opening_recap: bool = True                        # 前情提要
    cold_open: bool = True                            # 开场即冲突


# --------------------------------------------------------------------------- #
# Storyboard
# --------------------------------------------------------------------------- #
class StoryboardConfig(BaseModel):
    shots_per_scene: Literal["auto"] = "auto"
    min_shots_per_scene: int = 2
    max_shots_per_scene: int = 26
    # 一集最多几个镜头：一集五分钟，按镜头三到五秒算要六七十个
    max_shots_per_episode: int = 90
    # 一个片段的长度：视频模型一次出一段，段里可以有好几个镜头，
    # 切点由提示词里的时间戳决定。2 秒一切看着晕，所以片段要长。
    shot_duration_range: list[float] = Field(default_factory=lambda: [6.0, 15.0])
    prefer_dynamic: bool = True                       # 多用推拉摇移
    include_insert_shots: bool = True                 # 空镜/特写插入
    language: Literal["zh", "en", "bilingual"] = "bilingual"  # prompt language
    # 拉片结果：参考片的剪辑节奏，分镜按它的速度切
    ref_rhythm: dict = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Compose / render
# --------------------------------------------------------------------------- #
class ComposeConfig(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30
    video_bitrate: str = "6M"
    audio_bitrate: str = "192k"
    codec: str = "libx264"
    pixel_format: str = "yuv420p"
    crf: int = 20
    preset: str = "medium"
    transition: Literal["none", "fade", "dissolve"] = "fade"   # 场与场之间淡入淡出
    transition_duration: float = 0.35
    motion_effect: Literal["kenburns", "zoompan", "none"] = "kenburns"
    kenburns_scale: float = 1.12                      # max zoom for stills
    loudness_normalize: bool = True
    target_loudness_lufs: float = -16.0
    # MiniMax H3 原生音频（自带配乐/环境声/口型）的用法：
    #   bed     = H3 只出配乐+环境声，压在人声下面当垫底（人声完全由 TTS 轨负责）
    #   discard = 丢弃 H3 音频，只用 TTS 人声 + 曲库 BGM
    h3_audio: Literal["bed", "discard"] = "bed"
    h3_audio_gain: float = 0.18               # H3 垫底音量（相对人声）
    # 音乐垫底要比对白低这么多 LU 才听得清台词（每集会按实测自动校正）
    music_gap_lu: float = 12.0
    # --- 专业后期 ---
    # AI 镜头各自生成，曝光/饱和/白平衡各不相同，剪在一起会露馅。
    # 逐镜测量后统一到本集中位数，是"业余感"最大的单一来源。
    grade_shots: bool = True
    grade_strength: float = 0.85              # 0=不改，1=完全拉到目标
    lut: str = ""                             # 可选 .cube LUT，给全片套统一色调
    # H3 每镜生成的原生音频响度不一致，垫底时必须先归一，否则 BGM 忽大忽小
    normalize_bed_loudness: bool = True
    bed_target_lufs: float = -24.0            # 垫底比人声低，混音时再压
    # 导出 FCPXML 时间线，人可以在 Resolve / Premiere 里接着精修
    nle_export: bool = True
    # subtitles
    burn_subtitles: bool = True                       # 硬字幕（红果常用）
    also_write_srt: bool = True
    subtitle_style: dict = Field(default_factory=lambda: {
        "font": "Microsoft YaHei",
        "font_size": 30,          # 以 960 宽为基准，按画面宽度放大
        "primary_color": "&H00FFFFFF",   # white
        "outline_color": "&H00000000",   # black
        "outline": 2,
        "shadow": 0,
        "margin_v": 1,                      # distance from bottom, in text heights
        "margin_v_pct": 12.0,               # ... or as a share of the height:
        #                                   # in a tall frame the bottom is
        #                                   # where the platform's buttons are
        "bold": True,
        "alignment": 2,                  # bottom-center
        "speaker_color": "&H0000E5FF",   # 角色名 高亮
    })
    show_speaker_name: bool = False
    # 2026 年起 AIGC 微短剧必须标注 AI 生成，备案号也要上画面
    ai_declaration: str = "本片画面与声音由AI生成"
    ai_declaration_seconds: float = 3.0                        # 声明只放在片头几秒
    filing_number: str = ""                                 # 备案号（上线前填）
    film_grain: int = 4                                    # 胶片颗粒强度（去掉 AI 塑料感，0=关）
    # 口型对齐：画面里的嘴由模型自己动，录好的声音和嘴对不上，
    # 观众就会觉得声音飘在画面外。MuseTalk 用录好的音频重画嘴。
    # 台词上一点房间混响：干声铺在画面上会像飘在外面
    voice_room: float = 0.14
    lipsync: bool = False
    musetalk_root: str = r"E:\musetalk"
    musetalk_python: str = r"E:\ComfyUI\venv\Scripts\python.exe"
    lipsync_timeout: float = 900.0
    # 每句台词之间的留白（秒）。背靠背的台词听起来像在念清单，
    # 留半秒让对方接住，这是短剧的戏在的地方。
    line_gap: float = 0.5
    # cover
    generate_cover: bool = True
    cover_from_shot: Literal["first", "best", "last"] = "first"
    cover_title: bool = True                               # 封面烧上标题


# --------------------------------------------------------------------------- #
# Pipeline control
# --------------------------------------------------------------------------- #
class PipelineConfig(BaseModel):
    output_dir: str = "projects"
    stages_enabled: list[str] = Field(default_factory=lambda: [
        "ingest", "analyze", "character", "segment", "script", "storyboard",
        "promptgen", "visual", "voice", "subtitle", "music", "precheck",
        "compose", "qc",
    ])
    resume: bool = True                               # skip DONE nodes
    stop_after: Optional[str] = None                  # e.g. "storyboard"
    only_episodes: list[int] = Field(default_factory=list)   # [] = all
    fail_fast: bool = False
    verbose: bool = True


# --------------------------------------------------------------------------- #
# Root
# --------------------------------------------------------------------------- #
class Config(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    characters: CharacterConfig = Field(default_factory=CharacterConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    comfyui: ComfyUIConfig = Field(default_factory=ComfyUIConfig)
    music: MusicConfig = Field(default_factory=MusicConfig)
    segment: SegmentConfig = Field(default_factory=SegmentConfig)
    storyboard: StoryboardConfig = Field(default_factory=StoryboardConfig)
    compose: ComposeConfig = Field(default_factory=ComposeConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        """Load YAML config (deep-merged over defaults). Missing file => defaults.

        Keys whose value is null (e.g. a dict with only commented-out entries)
        are dropped so the model defaults apply instead of failing validation.
        """
        data: dict = {}
        if path and Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        return cls(**_drop_nulls(data))

    def resolve_llm(self, role: str = "") -> LLMConfig:
        """Pick the LLM config responsible for `role`.

        Registry first (priority order, then default). With no registry, keep
        the legacy split: `tag` uses ai.light_* when configured, everything
        else uses llm.
        """
        entry = self.models.pick(role)
        if entry is not None:
            return entry.to_llm(self.llm)
        if role == "tag" and self.ai.light_model and self.ai.light_base_url:
            return self.llm.model_copy(update={
                "base_url": self.ai.light_base_url,
                "api_key": self.ai.light_api_key or self.llm.api_key,
                "model": self.ai.light_model,
                "temperature": self.ai.light_temperature,
                "max_tokens": self.ai.light_max_tokens,
                "timeout": self.ai.light_timeout,
                "use_proxy": self.ai.light_use_proxy,
                "max_retries": 1,
            })
        return self.llm

    def dump_yaml(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.model_dump(), f, allow_unicode=True, sort_keys=False)
