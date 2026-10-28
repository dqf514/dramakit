"""Check that the stills are in the shape they will be shown in.

FLUX 3 takes the size of the picture from its reference, so a portrait
character sheet makes every still portrait, and a portrait still in a
landscape episode is cropped - which is what takes the faces off.
"""
from pathlib import Path

p = Path(r"E:\dramakit\qa.py")
s = p.read_text(encoding="utf-8")

old = """def check_framing(ctx, ep, tl, issues):"""
new = '''def check_shot_shape(ctx, ep, tl, issues):
    """Every still has to be in the shape of the episode."""
    dw = int(ctx.cfg.compose.width or 16)
    dh = int(ctx.cfg.compose.height or 9)
    want = dw / dh
    bad = []
    for ts in tl.shots:
        if not ts.shot.image_path:
            continue
        path = ctx.store.abs(ts.shot.image_path)
        if not path.exists():
            continue
        size = ff.image_size(path)
        if not size:
            continue
        w, h = size
        if h <= 0 or w <= 0:
            continue
        if abs((w / h) - want) > 0.04:
            bad.append((ts.shot.id, w, h))
    if bad:
        issues.append(("picture", "wrong_aspect", "-",
                       f"{len(bad)} 张首帧的比例和成片不符（{dw}x{dh}），"
                       f"会被裁掉："
                       + "、".join(f"{b[0]} {b[1]}x{b[2]}" for b in bad[:3])))
    return {"wrong": len(bad)}


def check_framing(ctx, ep, tl, issues):'''
assert old in s, "锚点没找到"
s = s.replace(old, new, 1)

old = """        e["framing"] = check_framing(ctx, ep, tl, issues)"""
new = """        e["framing"] = check_framing(ctx, ep, tl, issues)
        e["shot_shape"] = check_shot_shape(ctx, ep, tl, issues)"""
assert old in s, "framing 调用锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# the image size helper
p = Path(r"E:\dramakit\dramakit\media\ffmpeg.py")
s = p.read_text(encoding="utf-8")
old = """def extract_frame(video_or_image: str | Path, out: str | Path, at: float = 0.0,"""
new = """def image_size(path: str | Path) -> tuple[int, int]:
    \"\"\"The pixel size of a picture.\"\"\"
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, errors="replace")
    try:
        w, h = r.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except (ValueError, IndexError):
        return 0, 0


def extract_frame(video_or_image: str | Path, out: str | Path, at: float = 0.0,"""
assert old in s, "extract_frame 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("已加画幅检查")
