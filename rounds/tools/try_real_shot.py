"""One shot of the real episode, made the way the pipeline makes it.

The shot comes out of the project's own storyboard - the one-take
version - and it goes through the real prompt writer, the real picture
and the real video card.  The question is whether the face stays the
same through the clip, which is what the multi-cut version did not do.

    python rounds/tools/try_real_shot.py [episode] [shot-number]
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
from dramakit.pipeline.visual import _fit_refs, _ref_images, _shot_frames  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

PROJECT = "穿成亿万总裁他前妻"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode")
n_ep = int(sys.argv[1]) if len(sys.argv) > 1 else 1
n_shot = int(sys.argv[2]) if len(sys.argv) > 2 else 0

cfg = Config.load(Config.discover())
store = ProjectStore.open(ROOT / "projects" / PROJECT)
ctx = make_context(cfg, store)
llm = ctx.providers.llm
proj = store.load()
ep = next(e for e in proj.episodes if e.index == n_ep)

shots = [sh for sc in ep.scenes for sh in sc.shots]
with_lines = [sh for sh in shots if sh.line_indices]
print("  第%d集 %d 段，其中 %d 段带台词" % (n_ep, len(shots), len(with_lines)))
sh = with_lines[n_shot] if n_shot < len(with_lines) else with_lines[0]
sc = next(s for s in ep.scenes if sh in s.shots)
print("  选中: %s  %s  %ds  台词%s" % (sh.id[-6:], sh.shot_type.value, sh.duration, sh.line_indices))
print("  action:", (sh.action or "")[:200])

visuals = "\n".join(
    "%s：%s" % (c.name, c.description or c.appearance or "")
    for c in proj.characters if c.name in (sh.characters or []))
loc = next((l for l in proj.locations if l.name == sc.location), None)
location_visual = (loc.description if loc else "") or ""

_gen_image_prompt(ctx, llm, sh, sc, visuals, False, location_visual)
print()
print("=== 出图提示词 ===")
print(" ", (sh.prompt or "")[:700])

vis = ctx.providers.visual
img = OUT / "real_img.png"
t0 = time.time()
vis.generate_image(prompt=sh.prompt, negative=(sh.negative_prompt or ""),
                   width=cfg.comfyui.width, height=cfg.comfyui.height,
                   seed=4242, steps=cfg.comfyui.steps, cfg=cfg.comfyui.cfg,
                   out_path=str(img),
                   extra={"sampler": cfg.comfyui.sampler,
                          "scheduler": cfg.comfyui.scheduler,
                          "checkpoint": cfg.comfyui.checkpoint},
                   ref_images=_fit_refs(ctx, _ref_images(ctx, sh, sc), sh))
print("  图: %s（%d 秒）" % (img, int(time.time() - t0)))

dlg = []
for i in sh.line_indices:
    if 1 <= i <= len(sc.lines):
        ln = sc.lines[i - 1]
        dlg.append((ln.speaker, ln.text, 2.0))
_gen_h3_prompt(ctx, llm, sh, sc, visuals, location_visual, dlg, "")
print()
print("=== 视频提示词（H3）===")
print(" ", (sh.video_prompt or "")[:1200])
(OUT / "real_video_prompt.txt").write_text(sh.video_prompt or "", encoding="utf-8")

refs = _fit_refs(ctx, _ref_images(ctx, sh, sc), sh)
extra = {}
if cfg.comfyui.native_audio:
    for c in proj.characters:
        if c.name in (sh.characters or []) and c.voice_ref:
            extra = {"ref_audio_path": str(store.abs(c.voice_ref)),
                     "ref_audio_node": cfg.comfyui.ref_audio_node}
            break
extra["ref_pictures"] = refs
frames = _shot_frames(ctx, sh, float(sh.duration or 8.0))
print("  参考图 %d 张，帧数 %d，音频 %s" % (len(refs), frames, bool(extra.get("ref_audio_path"))))
vid = OUT / "real_clip.mp4"
t0 = time.time()
vis.generate_video(prompt=sh.video_prompt, negative="",
                   image_path=str(img), frames=frames, fps=cfg.comfyui.fps,
                   seed=4242, out_path=str(vid), extra=extra)
print("  视频: %s（%d 秒）" % (vid, int(time.time() - t0)))
