"""Does a picture come out?

The three things that stopped it, one after another: the workflow that
named a checkpoint the node cannot load, the ffmpeg that was not on
the machine's PATH, and the voice samples made with it.

This asks the provider for one picture, with the config as it is, and
says what came back.

    python rounds/tools/try_picture.py
"""
from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config  # noqa: E402

OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\try_picture.png")

PROMPT = ("cinematic film still, a young Chinese woman in a warm-lit apartment at night, "
          "she stands by the window, soft bokeh city lights behind her, natural skin texture, "
          "dramatic key light, shallow depth of field")


def main() -> int:
    cfg = Config.load(Config.discover())
    c = cfg.comfyui
    print("  出图工作流:", c.t2i_workflow)
    print("  带参考图的:", c.t2i_workflow_ref)
    print("  模型:", c.checkpoint)
    print("  文本编码器:", c.clip_name)
    print("  VAE:", c.vae_name)
    print("  分辨率: %sx%s  步数 %s" % (c.width, c.height, c.steps))

    from dramakit.providers.comfyui import ComfyUIClient

    prov = ComfyUIClient(c)
    t0 = time.time()
    try:
        prov.generate_image(
            prompt=PROMPT, negative="",
            width=c.width, height=c.height,
            seed=20261106, steps=c.steps, cfg=c.cfg,
            out_path=str(OUT),
            extra={"sampler": c.sampler, "scheduler": c.scheduler,
                   "checkpoint": c.checkpoint})
    except Exception as e:  # noqa: BLE001
        print("  **出图失败**：", str(e)[:400])
        return 1
    dt = int(time.time() - t0)
    if OUT.exists() and OUT.stat().st_size > 0:
        print("  出图成功：%s（%.1f KB，%d 秒）" % (OUT, OUT.stat().st_size / 1024, dt))
        return 0
    print("  **没有图**")
    return 1


if __name__ == "__main__":
    sys.exit(main())
