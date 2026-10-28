"""Put the delivery back into the portrait frame it was designed for.

The storyboard was told to plan a 9:16 drama and the actions it wrote say
"竖屏中景" - but the pictures were made 1344x768 and the episode was
delivered 960x544. The picture and the script contradicted each other,
and the model that watched the finished episode named it as the worst
problem: a short drama is watched on a phone, in a tall frame.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\default.yaml")
lines = p.read_text(encoding="utf-8").splitlines()


def set_line(prefix: str, new: str) -> bool:
    for i, l in enumerate(lines):
        if l.strip().startswith(prefix):
            lines[i] = new
            return True
    return False


# the picture (FLUX 3 and H3 both want multiples of 32)
set_line("width: 1344",
         "  width: 768                              # 出图分辨率（FLUX 3 / H3 都吃 32 的倍数）")
set_line("height: 768",
         "  height: 1344                            # 9:16 竖屏原生（短剧就是竖着看的）")
# the clip H3 makes
set_line("video_width: 960",
         "  video_width: 768")
set_line("video_height: 544",
         "  video_height: 1344")
# the episode that goes out
set_line("width: 960",
         "  width: 1080")
set_line("height: 544",
         "  height: 1920                            # 9:16 竖屏成片（平台标准）")

p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("yaml 已改成竖屏")
