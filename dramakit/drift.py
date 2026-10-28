"""Ask a model whether the face drifted over the shot.

The picture drifts slowly over a long take: the last frame is not the
person the first frame showed, and the eye only catches it if the two are
put side by side. This puts them side by side and asks.

    dj drift 轮次09_09
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

SYSTEM = """你是短剧画面质检员。给你的每一对图片是同一个镜头的**第一帧**和**最后一帧**，
你要判断这个镜头里人物的脸有没有漂移。

"漂移"指这些：
- 脸型变了（五官比例变化、眼睛大小变了、鼻子形状变了、嘴形变了、下颌线变了）
- 脸变长、变窄、变胖，或者五官被拉长压扁
- 年龄、性别、发型变了
- 多出或少了五官，或者皮肤变成塑料一样

判断时只比较同一个人的脸，不要因为镜头运动或光影变化就说漂移。

只输出 JSON：
{"逐镜":[{"镜号":1,"漂移":0-3,"问题":"","画面里的人":""}],
 "最严重的镜头":"","总结":""}

0 = 完全没漂移；1 = 轻微，要盯着看才发现；2 = 明显看得出来；3 = 已经不是同一个人了。
"问题"用一句话说清楚漂在哪里；没有问题就写"无"。"""


def _pairs(ctx: Context, ep, tmp: Path) -> list[tuple[str, list[Path]]]:
    """The first and the last frame of every shot."""
    tl = ctx.timeline(ep)
    out: list[tuple[str, list[Path]]] = []
    for i, ts in enumerate(tl.shots, 1):
        if not ts.shot.video_path:
            continue
        src = ctx.store.abs(ts.shot.video_path)
        if not src.exists():
            continue
        frames = []
        for tag, at in (("a", 0.08), ("b", max(ts.duration - 0.12, 0.1))):
            p = tmp / f"drift_{i:02d}_{tag}.jpg"
            try:
                ff.extract_frame(src, p, at=at, width=640)
            except Exception:  # noqa: BLE001
                continue
            if p.exists():
                frames.append(p)
        if len(frames) == 2:
            out.append((f"镜{i}（{ts.shot.shot_type.value}，"
                        f"画面里有{'、'.join(ts.shot.characters or []) or '无人'}，"
                        f"时长 {ts.duration:.1f} 秒）", frames))
    return out


def drift(project: str, cfg: Config, *, save: Optional[str] = None) -> dict:
    root = Path(project)
    if not root.is_absolute():
        root = Path("projects") / root
    store = ProjectStore(root)
    ctx = Context(cfg, store)
    ep = ctx.target_episodes()[0]
    tmp = root / "tmp" / "drift"
    tmp.mkdir(parents=True, exist_ok=True)
    pairs = _pairs(ctx, ep, tmp)
    if not pairs:
        return {"error": "没有镜头视频"}

    content_lines = ["下面是每个镜头的第一帧和最后一帧，请逐镜判断人脸有没有漂移："]
    images: list[str] = []
    for label, frames in pairs:
        content_lines.append(f"{label}：接着的两张图依次是第一帧、最后一帧")
        images += [str(p) for p in frames]

    llm = ctx.providers.llm_for("review")
    r = llm.complete_vision(SYSTEM, "\n".join(content_lines), images,
                            temperature=0.1, max_tokens=24000)
    text = r.text.strip()
    try:
        data = json.loads(re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip())
    except Exception:  # noqa: BLE001
        data = {"原文": text}
    out = Path(save) if save else (root / "drift.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
