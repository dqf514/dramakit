"""One segment of ten seconds, made the way the pipeline makes it.

The user asked for a ten second clip and not a whole episode: the
point is to see whether the picture has depth and whether the segment
has cuts, and that is a question about one segment.

So: a shot with five cuts written the way the code reads them, the
real prompt written by the real template, the real picture from the
real card, and the real clip from the video card.

    python rounds/tools/try_ten_seconds.py
"""
from __future__ import annotations

import pathlib
import sys
import time

ROOT = pathlib.Path(r"E:\dramakit")
sys.path.insert(0, str(ROOT))

from dramakit.config import Config  # noqa: E402
from dramakit.models import Line, Scene, Shot  # noqa: E402
from dramakit.pipeline.promptgen import _gen_h3_prompt, _gen_image_prompt  # noqa: E402
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
               summary="夏一朵在陌生卧室醒来，陌生的记忆开始涌来",
               mood="慌乱")
    sc.lines.append(Line(id="ln-1", speaker="陈嫂", text="太太，起床了吗？", emotion="礼貌"))
    sc.lines.append(Line(id="ln-2", speaker="夏一朵", text="你、你是谁？", emotion="惊慌"))
    sh = Shot(id="sh-test", index=0, shot_type="中景", angle="斜侧",
              height="平视", lens="标准", camera_move="固定",
              subject="夏一朵的眼睛", purpose="她在陌生的地方醒来",
              duration=10.0, action=ACTION,
              characters=["夏一朵", "陈嫂"], line_indices=[1, 2])
    sc.shots.append(sh)

    print("=== 段内的刀口（代码读的格式）===")
    from dramakit.pipeline.promptgen import _segment_beats
    for i, (a, b, what) in enumerate(_segment_beats(sh), 1):
        print("  [Shot %d] %.1f-%.1f秒  %s" % (i, a, b, what[:70]))

    visuals = "夏一朵：22岁，齐下巴黑色直发，浅色丝质睡袍；陈嫂：50岁，深色管家制服"
    location_visual = "庄园主卧：床位居中，落地玻璃在左侧，超大抽象画在右墙，水晶吊灯在顶部"
    _gen_image_prompt(ctx, llm, sh, sc, visuals, False, location_visual)
    print()
    print("=== 出图提示词 ===")
    print(" ", (sh.prompt or "")[:900])

    vis = ctx.providers.visual
    img = OUT / "ten_img.png"
    t0 = time.time()
    vis.generate_image(prompt=sh.prompt, negative=(sh.negative_prompt or ""),
                       width=cfg.comfyui.width, height=cfg.comfyui.height,
                       seed=4242, steps=cfg.comfyui.steps, cfg=cfg.comfyui.cfg,
                       out_path=str(img),
                       extra={"sampler": cfg.comfyui.sampler,
                              "scheduler": cfg.comfyui.scheduler,
                              "checkpoint": cfg.comfyui.checkpoint})
    print("  图: %s（%d 秒）" % (img, int(time.time() - t0)))

    dlg = {"sh-test": [("陈嫂", "太太，起床了吗？", 2.0), ("夏一朵", "你、你是谁？", 2.0)]}
    _gen_h3_prompt(ctx, llm, sh, sc, visuals, location_visual, dlg, "")
    print()
    print("=== 视频提示词（H3 三字段）===")
    print(" ", (sh.video_prompt or "")[:1200])

    vid = OUT / "ten_clip.mp4"
    t0 = time.time()
    vis.generate_video(prompt=sh.video_prompt, negative="",
                       image_path=str(img), frames=240, fps=24, seed=4242,
                       out_path=str(vid))
    print("  视频: %s（%d 秒）" % (vid, int(time.time() - t0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
