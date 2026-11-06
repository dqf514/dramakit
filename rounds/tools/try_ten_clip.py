"""The ten second clip, on its own.

The picture is made; this makes the clip: the H3 prompt written by the
real template, and the video card asked for ten seconds.

    python rounds/tools/try_ten_clip.py
"""
from __future__ import annotations

import pathlib
import sys
import time

ROOT = pathlib.Path(r"E:\dramakit")
sys.path.insert(0, str(ROOT))

from dramakit.config import Config  # noqa: E402
from dramakit.models import Line, Scene, Shot  # noqa: E402
from dramakit.pipeline.promptgen import _gen_h3_prompt  # noqa: E402
from dramakit.pipeline.runner import make_context  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

PROJECT = "穿成亿万总裁他前妻"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode")

ACTION = (
    "镜头1（0.0-2.2秒）：全景，庄园主卧清晨，厚地毯上夏一朵赤足走向落地窗，"
    "窗帘半开，晨光斜切进来；"
    "镜头2（2.2-4.5秒）：近景，她的手在床头柜上摸索，碰到开关，窗帘哗地一下全开，"
    "光涌进来；"
    "镜头3（4.5-6.8秒）：特写，她的脸被强光打亮，瞳孔收缩，没有眼镜的视线是模糊的；"
    "镜头4（6.8-8.6秒）：过肩，越过她的肩看房门外，陈嫂站在门口端着早餐托盘；"
    "镜头5（8.6-10.0秒）：中近景，陈嫂的脸，她察觉不对，眉头一皱"
)


def main() -> int:
    cfg = Config.load(Config.discover())
    store = ProjectStore.open(ROOT / "projects" / PROJECT)
    ctx = make_context(cfg, store)
    llm = ctx.providers.llm

    sc = Scene(id="sc-test", index=1, location="主卧睡眠区", time_of_day="晨",
               summary="夏一朵在陌生卧室醒来，陌生的记忆开始涌来", mood="慌乱")
    sc.lines.append(Line(id="ln-1", speaker="陈嫂", text="太太，起床了吗？", emotion="礼貌"))
    sc.lines.append(Line(id="ln-2", speaker="夏一朵", text="你、你是谁？", emotion="惊慌"))
    sh = Shot(id="sh-test", index=0, shot_type="中景", angle="斜侧",
              height="平视", lens="标准", camera_move="固定",
              subject="夏一朵的眼睛", purpose="她在陌生的地方醒来",
              duration=10.0, action=ACTION,
              characters=["夏一朵", "陈嫂"], line_indices=[1, 2])
    sc.shots.append(sh)

    visuals = "夏一朵：22岁，齐下巴黑色直发，浅色丝质睡袍；陈嫂：50岁，深色管家制服"
    location_visual = "庄园主卧：床位居中，落地玻璃在左侧，超大抽象画在右墙，水晶吊灯在顶部"
    dlg = {"sh-test": [("陈嫂", "太太，起床了吗？", 2.0), ("夏一朵", "你、你是谁？", 2.0)]}
    _gen_h3_prompt(ctx, llm, sh, sc, visuals, location_visual, dlg, "")
    print("=== 视频提示词 ===")
    print((sh.video_prompt or "")[:1500])
    (OUT / "ten_video_prompt.txt").write_text(sh.video_prompt or "", encoding="utf-8")

    vis = ctx.providers.visual
    vid = OUT / "ten_clip.mp4"
    t0 = time.time()
    vis.generate_video(prompt=sh.video_prompt, negative="",
                       image_path=str(OUT / "ten_img.png"),
                       frames=240, fps=24, seed=4242, out_path=str(vid))
    print("  视频: %s（%d 秒）" % (vid, int(time.time() - t0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
