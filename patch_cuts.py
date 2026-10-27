"""The cuts the viewer cannot see.

The timeline says where the shots change, but if two shots in a row look
almost the same, the change does not read as a cut - the viewer sees a
jump instead. That is the difference between cutting fast and cutting
well.
"""
from pathlib import Path

p = Path(r"E:\dramakit\qa.py")
s = p.read_text(encoding="utf-8")

old = """def check_rhythm(ctx, ep, tl, issues):"""
new = '''def check_visible_cuts(ctx, ep, tl, issues):
    """Every cut on the timeline has to be a cut the viewer can see."""
    path = ctx.store.abs(ep.video_path) if ep.video_path else None
    if not path or not path.exists():
        return {}
    from dramakit.ref_rhythm import analyse
    p = analyse(Path(path))
    if not p.get("shots"):
        return {}
    detected = p.get("cut_times") or []
    invisible = []
    for sc in tl.scenes:
        bounds = [ts.start for ts in sc.shots[1:]]
        for b in bounds:
            if not any(abs(b - d) < 0.45 for d in detected):
                invisible.append(round(b, 2))
    if invisible:
        issues.append(("rhythm", "invisible_cut", "-",
                       f"{len(invisible)} 个切点观众看不出来（前后两个镜头太像）："
                       + "、".join(f"{t:.1f}s" for t in invisible[:4])))
    return {"cuts": len(detected), "invisible": len(invisible)}


def check_rhythm(ctx, ep, tl, issues):'''
assert old in s, "rhythm 锚点没找到"
s = s.replace(old, new, 1)

old = """        e["rhythm"] = check_rhythm(ctx, ep, tl, issues)"""
new = """        e["rhythm"] = check_rhythm(ctx, ep, tl, issues)
        e["visible_cuts"] = check_visible_cuts(ctx, ep, tl, issues)"""
assert old in s, "rhythm 调用锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")

# the rhythm profile has to carry the cut times
p = Path(r"E:\dramakit\dramakit\ref_rhythm.py")
s = p.read_text(encoding="utf-8")
old = """        "cuts_per_min": round(len(cuts) / max(dur / 60.0, 1e-6), 1),
        "shot_lengths": lengths[:120],"""
new = """        "cuts_per_min": round(len(cuts) / max(dur / 60.0, 1e-6), 1),
        "cut_times": cuts[:120],
        "shot_lengths": lengths[:120],"""
assert old in s, "profile 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

print("可见切点检查已加")
