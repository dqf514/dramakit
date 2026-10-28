"""Have a model watch the episode and say what is wrong with it.

The numbers the QA measures are objective but blind: they can say that a
shot is too long, not that the man is not looking at the woman he is
talking to. A multimodal model can look at the frames and say what the
numbers cannot - where the picture and the sound come apart, where the
acting is dead, where the hook is missing.

    dj review 轮次09_09
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from .config import Config
from .media import ffmpeg as ff
from .pipeline.base import Context, build_timeline
from .project import ProjectStore

SYSTEM = """你是红果短剧的资深责编兼导演，看过几千部短剧，也亲手带过 AI 短剧的流水线。
你会拿到一集成片的关键帧（每张图下面写着这是第几个镜头、时长、景别、谁在画面里、
这个镜头承载哪句台词），以及机器测出来的客观数据。

你的任务不是夸奖，是把这集当成要上线赚钱的片子来挑毛病。请重点看：

1. **画面**：人物长相是否一致、姿态是否自然、有没有脸崩/手崩/穿帮、构图是不是"证件照"、
   景别有没有变化、视线是不是对得上
2. **音画关系**：声音和画面对不对得上——嘴在不在动、说话的人和镜头里的人是不是同一个、
   音乐是不是和场景打架、有没有"声音飘在画面外"的感觉
3. **节奏**：开场三秒有没有钩子、镜头是不是太长或太碎、转折有没有落在画面上
4. **表演**：情绪有没有演出来、有没有"念台词"的痕迹

只输出 JSON，结构：
{
  "总分": 0-100,
  "各维度": {"画面": 0-100, "音画关系": 0-100, "节奏": 0-100, "表演": 0-100},
  "最严重的三个问题": [{"问题": "", "出现在哪个镜头": "", "为什么是问题": "", "流水线该改哪里": ""}],
  "做得好的地方": [""],
  "和爆款短剧的差距": ""
}
"流水线该改哪里"要具体到能改代码或改提示词，不能是"再打磨一下"这种话。"""


def _frames(ctx: Context, ep, tmp: Path, limit: int = 12) -> list[Path]:
    """One frame per shot, taken from the finished episode."""
    tl = ctx.timeline(ep)
    path = ctx.store.abs(ep.video_path) if ep.video_path else None
    if not path or not path.exists():
        return []
    out: list[Path] = []
    shots = tl.shots
    step = max(1, len(shots) // limit)
    for i, ts in enumerate(shots):
        if i % step:
            continue
        at = ts.start + ts.duration * 0.45
        p = tmp / f"review_{i:02d}.jpg"
        try:
            ff.extract_frame(path, p, at=at, width=768)
        except Exception:  # noqa: BLE001
            continue
        if p.exists():
            out.append(p)
    return out


def _facts(ctx: Context, ep) -> str:
    """What the machine measured, in words."""
    tl = ctx.timeline(ep)
    lines = [f"成片时长 {tl.duration:.1f} 秒，共 {len(tl.shots)} 个镜头",
             f"画幅 {ctx.cfg.compose.width}x{ctx.cfg.compose.height}"]
    for i, ts in enumerate(tl.shots, 1):
        who = "、".join(ts.shot.characters or []) or "（无人）"
        lines.append(f"  镜{i}: {ts.duration:.1f}s {ts.shot.shot_type.value} "
                     f"运镜{ts.shot.camera_move} 画面里有：{who}")
    voiced = [t for t in tl.lines if t.line.kind.value == "dialogue"]
    if voiced:
        lines.append("台词顺序与时间：")
        for t in voiced:
            lines.append(f"  {t.start:5.1f}s-{t.end:5.1f}s "
                         f"{t.line.speaker}：「{t.line.text}」")
    return "\n".join(lines)


def review(project: str, cfg: Config, *, limit: int = 12,
           save: Optional[str] = None) -> dict:
    root = Path(project)
    if not root.is_absolute():
        root = Path("projects") / root
    store = ProjectStore(root)
    ctx = Context(cfg, store)
    ep = ctx.target_episodes()[0]
    tmp = root / "tmp" / "review"
    tmp.mkdir(parents=True, exist_ok=True)
    frames = _frames(ctx, ep, tmp, limit=limit)
    if not frames:
        return {"error": "没有成片或抽不出帧"}
    facts = _facts(ctx, ep)
    llm = ctx.providers.llm_for("review")
    # M3 is a reasoning model: it spends the tokens on thinking first, and a
    # small budget leaves the answer empty (finish_reason "length")
    r = llm.complete_vision(SYSTEM, facts, [str(p) for p in frames],
                            temperature=0.2, max_tokens=24000)
    text = r.text.strip()
    try:
        data = json.loads(re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip())
    except Exception:  # noqa: BLE001
        data = {"原文": text}
    out = Path(save) if save else (root / "review.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
