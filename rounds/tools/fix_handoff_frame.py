"""The handoff is a frame, not a file.

The slot in the list points at the shot before's video, because the list
is built before that video exists and the numbers have to match.  When the
video is there, its last frame is the picture the next shot continues
from, so the frame is taken out of it and that is what goes in.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py")
s = p.read_text(encoding="utf-8")

old = """        plan = [p for p, _role, _kind in picture_plan(ctx, shot, sc)]
        meta["references"] = len(plan)"""
new = """        plan = [p for p, _role, _kind in picture_plan(ctx, shot, sc)]
        plan = [_handoff_frame(ctx, shot, sc, x) for x in plan]
        meta["references"] = len(plan)"""
assert old in s, "清单锚点没找到"
s = s.replace(old, new, 1)

old2 = "def _wait_for_still(ctx: Context, shot: Shot, sc, minutes: float = 30.0) -> list[str]:"
new2 = '''def _handoff_frame(ctx: Context, shot: Shot, sc, path: str) -> str:
    """The last frame of the shot before, as a picture.

    The list points at the shot before's video - the list is built before
    that video exists, and the numbers have to match the prompt.  With the
    video there, the frame the next shot continues from is its last one.
    """
    if not path.endswith((".mp4", ".mov", ".mkv", ".webm")):
        return path
    src = Path(path)
    if not src.exists():
        return path
    out = ctx.store.root / "tmp" / f"handoff_{src.stem}.png"
    try:
        if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
            out.parent.mkdir(parents=True, exist_ok=True)
            from ..media import ffmpeg as ff
            ff._run([ff.ffmpeg_bin(), "-y", "-sseof", "-0.1", "-i", str(src),
                     "-frames:v", "1", str(out)], quiet=True)
        return str(out) if out.exists() else path
    except Exception:  # noqa: BLE001
        return path


def _wait_for_still(ctx: Context, shot: Shot, sc, minutes: float = 30.0) -> list[str]:'''
assert old2 in s, "函数插入锚点没找到"
s = s.replace(old2, new2, 1)
p.write_text(s, encoding="utf-8")
print("visual.py: 交接帧会从上一段视频里抽出来")
