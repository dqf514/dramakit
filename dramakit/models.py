"""Data models for a short-drama project.

The whole pipeline is a series of transformations over this tree:

    Project
      └── Episode            (一集, 竖屏 1~2 分钟)
            └── Scene        (一场戏, 同一时空)
                  ├── Line   (一句台词 / 旁白)
                  └── Shot   (一个分镜 / 一个生成单元)

Every node carries a `status` so the runner can resume after a crash or a
partial run. Assets (audio / image / video / subtitle files) are referenced by
paths relative to the project directory.
"""
from __future__ import annotations

import enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Status / enums
# --------------------------------------------------------------------------- #
class Status(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class LineKind(str, enum.Enum):
    DIALOGUE = "dialogue"      # 角色对白
    NARRATION = "narration"    # 旁白 / 解说
    MONOLOGUE = "monologue"    # 内心独白
    CAPTION = "caption"        # 屏幕字幕卡（时间/地点提示）


class ShotType(str, enum.Enum):
    EXTREME_CLOSE = "特写"     # ECU
    CLOSE = "近景"             # CU
    MEDIUM = "中景"            # MS
    FULL = "全景"              # FS
    WIDE = "远景"              # WS
    OVER_SHOULDER = "过肩"     # OTS
    POV = "主观"               # POV
    INSERT = "空镜"            # insert / cutaway


NARRATOR = "旁白"
NARRATOR_SPEAKERS = {NARRATOR, "解说", "旁白者"}


def is_narration(line: "Line") -> bool:
    """True for lines that are shown as narration cards, not spoken dialogue.

    Narration / caption lines carry the story voice-over; they are rendered as
    their own on-screen text form and are not synthesized by the voice stage.
    """
    return (line.kind in (LineKind.NARRATION, LineKind.CAPTION)
            or line.speaker in NARRATOR_SPEAKERS)


# --------------------------------------------------------------------------- #
# World / characters (produced by the analyze stage)
# --------------------------------------------------------------------------- #
class Character(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    role: str = "配角"                       # 主角 / 女主 / 反派 / 配角 ...
    gender: str = "未知"
    age: str = ""
    personality: str = ""
    appearance: str = ""                     # 外貌，用于画面一致性
    visual_prompt: str = ""                  # 稳定的英文出图描述
    outfit: str = ""                         # 固定服装（跨镜头不变）
    hair: str = ""                           # 固定发型/发色
    anchor_prompt: str = ""                  # 角色锁定锚点：每次出图前置注入
    negative_prompt: str = ""                # 角色专属负面词
    consistency: str = ""                    # 空=跟随全局；prompt/ref/lora
    ref_images: list[str] = Field(default_factory=list)  # 三视图/参考图
    ref_sheet: str = ""                      # 主参考图（角色卡封面）
    locked: bool = False                     # 锁定后角色锚点不允许被 AI 改写
    voice_id: str = ""                       # 绑定音色
    voice_pitch: str = ""                    # 专属音高微调，如 "-16Hz"（随定妆一起设计）
    voice_rate: str = ""                     # 专属语速微调，如 "-10%"
    ref_image: str = ""                      # 旧版单图字段，兼容保留
    lora: str = ""                           # 角色 LoRA（ComfyUI 用）

    def matches(self, token: str) -> bool:
        t = token.strip()
        return t == self.name or any(t == a for a in self.aliases)

    def anchor(self) -> str:
        """Stable text block injected before every shot prompt."""
        if self.anchor_prompt:
            return self.anchor_prompt
        bits = [self.visual_prompt or self.appearance, self.hair, self.outfit]
        return ", ".join(b.strip().rstrip(",") for b in bits if b and b.strip())

    def refs(self) -> list[str]:
        out = list(self.ref_images)
        if self.ref_image and self.ref_image not in out:
            out.insert(0, self.ref_image)
        return out


class Location(BaseModel):
    name: str
    description: str = ""
    visual_prompt: str = ""
    ref_images: list[str] = Field(default_factory=list)


class Prop(BaseModel):
    """One recurring object the story keeps returning to."""
    name: str
    description: str = ""
    visual_prompt: str = ""                 # english, for the picture
    ref_images: list[str] = Field(default_factory=list)
    ref_sheet: str = ""


class ArtDirection(BaseModel):
    genre: str = "都市"
    style: str = "写实电影感"
    aspect_ratio: str = "9:16"
    era: str = "当代"
    color_palette: str = ""
    global_negative_prompt: str = (
        "lowres, bad anatomy, extra fingers, text, watermark, logo, blurry, "
        "distorted face, deformed hands"
    )
    style_prompt_prefix: str = ""            # 拼在每个镜头 prompt 前


# --------------------------------------------------------------------------- #
# Script-level nodes
# --------------------------------------------------------------------------- #
class Line(BaseModel):
    id: str
    kind: LineKind = LineKind.DIALOGUE
    speaker: str = NARRATOR
    text: str
    emotion: str = "平静"                     # 平静/愤怒/悲伤/惊讶/喜悦...
    audio_path: str = ""
    duration: float = 0.0                     # seconds, filled by voice stage
    status: Status = Status.PENDING


class Shot(BaseModel):
    id: str
    index: int = 0
    shot_type: ShotType = ShotType.MEDIUM
    camera_move: str = "固定"                 # 固定/推/拉/摇/移/跟
    duration: float = 3.0                     # seconds
    action: str = ""                          # 画面内容（中文，给人看）
    characters: list[str] = Field(default_factory=list)
    # which lines of the scene this shot carries (1-based). The timeline cuts
    # on these, so the camera is on the person who is speaking.
    line_indices: list[int] = Field(default_factory=list)
    # generation
    prompt: str = ""                          # 正向提示词（出图用）
    negative_prompt: str = ""
    video_prompt: str = ""                     # MiniMax H3 官方三字段提示词（出视频用）
    end_prompt: str = ""                      # 尾帧提示词（首尾帧模式）
    seed: int = -1                            # -1 = 随机
    flf: Optional[bool] = None                # 首尾帧：None=跟随全局，False=覆盖关闭
    # assets
    image_path: str = ""                      # 首帧 / 静帧
    end_image_path: str = ""                  # 尾帧
    video_path: str = ""
    status: Status = Status.PENDING
    gen_meta: dict = Field(default_factory=dict)   # ComfyUI 返回信息

    @property
    def has_visual(self) -> bool:
        return bool(self.image_path or self.video_path)


class Scene(BaseModel):
    id: str
    index: int = 0
    location: str = ""
    time_of_day: str = "日"                   # 日/夜/晨/昏
    summary: str = ""
    mood: str = "中性"                        # 用于配乐情绪匹配
    bgm_mood: str = ""                        # 覆盖 scene.mood 的配乐标签
    score_prompt: str = ""                    # 这一场的纯配乐镜头提示词（H3 三字段）
    lines: list[Line] = Field(default_factory=list)
    shots: list[Shot] = Field(default_factory=list)
    status: Status = Status.PENDING

    @property
    def narration_seconds(self) -> float:
        return round(sum(l.duration for l in self.lines), 2)


class Episode(BaseModel):
    id: str
    index: int = 1
    title: str = ""
    logline: str = ""                         # 一句话剧情
    hook: str = ""                            # 结尾钩子/悬念
    recap: str = ""                           # 前情提要
    key_beats: list[str] = Field(default_factory=list)
    source_path: str = ""                     # project-relative path to this ep's source text
    duration_target: float = 90.0             # seconds
    scenes: list[Scene] = Field(default_factory=list)
    cover_path: str = ""
    video_path: str = ""
    subtitle_path: str = ""
    ass_path: str = ""
    voice_path: str = ""                      # assembled dialogue track
    bgm_path: str = ""
    status: Status = Status.PENDING
    stage_status: dict[str, Status] = Field(default_factory=dict)
    compose_blocked: str = ""                  # precheck 阶段写入的阻断原因（空=可合成）
    qc_report: dict = Field(default_factory=dict)   # qc 阶段的成片质检报告

    @property
    def total_shots(self) -> int:
        return sum(len(s.shots) for s in self.scenes)

    @property
    def estimated_seconds(self) -> float:
        return round(sum(sh.duration for s in self.scenes for sh in s.shots), 2)


# --------------------------------------------------------------------------- #
# Subtitles
# --------------------------------------------------------------------------- #
class SubtitleCue(BaseModel):
    start: float
    end: float
    speaker: str = ""
    text: str
    kind: LineKind = LineKind.DIALOGUE


# --------------------------------------------------------------------------- #
# Project root
# --------------------------------------------------------------------------- #
class ProjectMeta(BaseModel):
    name: str
    source_file: str = ""
    title: str = ""
    author: str = ""
    synopsis: str = ""
    created_at: str = ""
    updated_at: str = ""


class Project(BaseModel):
    """Persisted as project.json inside the project directory."""
    schema_version: int = 1
    meta: ProjectMeta
    art_direction: ArtDirection = Field(default_factory=ArtDirection)
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    props: list[Prop] = Field(default_factory=list)
    episodes: list[Episode] = Field(default_factory=list)
    stage_status: dict[str, Status] = Field(default_factory=dict)

    def character(self, name: str) -> Optional[Character]:
        for c in self.characters:
            if c.matches(name):
                return c
        return None

    def episode(self, index: int) -> Optional[Episode]:
        for e in self.episodes:
            if e.index == index:
                return e
        return None

    @property
    def total_shots(self) -> int:
        return sum(e.total_shots for e in self.episodes)
