"""16:9, 1024x576, and a face that fills the frame.

Three things the brief asks for:

  * everything is landscape now - the pictures, the clips and the finished
    episode are 16:9 at 1024x576.  The pipeline is still being tested and
    tuned, so the picture stays small: a bigger one costs the time that
    should go into the work.
  * the reference pictures are the same size.
  * a character is only as consistent as the picture the model is given,
    and a face in a full-body shot is a small face.  So the reference
    carries a shot of the face filling the frame.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")


def patch(path: str, pairs: list[tuple[str, str]]) -> None:
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s and old not in s:
            print(f"  {path}: 已经打过补丁了")
            continue
        assert old in s, f"{path}: 锚点没找到\n{old[:200]}"
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"  {path}: 改好了")


# --------------------------------------------------------------------------- #
# 1. the config: landscape, 1024x576
# --------------------------------------------------------------------------- #
patch("config/default.yaml", [
    ("  ref_views: [front, side, three_quarter, back]   # 角色资产图：正面/侧面/四分之三/背面\n"
     "  ref_width: 768\n"
     "  ref_height: 1024",
     "  ref_views: [front, face, side, three_quarter, back]  # 角色资产图：正面全身/面部满屏/侧面/四分之三/背面\n"
     "  ref_width: 1024                               # 参考图跟出图同尺寸（16:9）\n"
     "  ref_height: 576"),
    ("  width: 768                              # 出图分辨率（FLUX 3 / H3 都吃 32 的倍数）\n"
     "  height: 1344                            # 9:16 竖屏原生（短剧就是竖着看的）",
     "  width: 1024                             # 出图分辨率（FLUX 3 / H3 都吃 32 的倍数）\n"
     "  height: 576                             # 16:9 横屏"),
    ("  video_width: 576\n  video_height: 1024",
     "  video_width: 1024                      # 16:9 横屏\n  video_height: 576"),
    ("  width: 1080\n  height: 1920                            # 9:16 竖屏成片（平台标准）",
     "  width: 1024\n  height: 576                             # 16:9 横屏成片"),
])
