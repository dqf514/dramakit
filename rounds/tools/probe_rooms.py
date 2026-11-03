"""How many shots the room check will refuse, and why.

The drawers are running, but some shots are being failed before they are
sent: a shot whose scene has no room asset has no reference for the room,
and the rule is that a video is not drawn without its references. That
rule is right when the asset is missing by accident and wrong when the
book simply has no room art yet - in the second case it stops the whole
scene rather than one picture.

So the scenes are counted against the locations, and the locations
against their pictures, to see whether this is a few broken entries or a
missing piece of the project.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))

locs = raw.get("locations") or []
out.append(f"=== 房间资产 {len(locs)} 个 ===")
by_name = {}
for l in locs:
    if not isinstance(l, dict):
        continue
    by_name[l.get("name")] = l
    refs = l.get("ref_images") or []
    have = [r for r in refs if (proj / r).exists()]
    out.append(f"  {l.get('name')!r}: 参考图 {len(refs)} 个，磁盘上有 {len(have)} 个")

out.append("")
out.append("=== 各集用到的场景 ===")
scene_use: dict[str, int] = {}
shots_by_loc: dict[str, list] = {}
total_shots = 0
no_loc_asset = 0
no_ref_pic = 0
ok_shots = 0
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        loc = sc.get("location")
        n = len(sc.get("shots") or [])
        scene_use[loc] = scene_use.get(loc, 0) + n
        for sh in sc.get("shots") or []:
            total_shots += 1
            shots_by_loc.setdefault(loc, []).append(sh.get("id"))
            if loc not in by_name:
                no_loc_asset += 1
            elif not any((proj / r).exists()
                         for r in (by_name[loc].get("ref_images") or [])):
                no_ref_pic += 1
            else:
                ok_shots += 1

for loc, n in sorted(scene_use.items(), key=lambda x: -x[1]):
    l = by_name.get(loc)
    state = ("无房间资产" if l is None else
             f"有资产，参考图磁盘上 {len([r for r in (l.get('ref_images') or []) if (proj/r).exists()])} 张")
    out.append(f"  {loc!r:34} {n:>3} 镜   {state}")

out.append("")
out.append("=== 汇总 ===")
out.append(f"  镜头总数 {total_shots}")
out.append(f"  场景资产缺失（会被判失败）: {no_loc_asset}")
out.append(f"  有资产但没参考图（会被判失败）: {no_ref_pic}")
out.append(f"  参考图齐全（可渲染）: {ok_shots}")

# does the check have a config escape?
out.append("")
out.append("=== 相关配置 ===")
from dramakit.config import Config    # noqa: E402
cfg = Config.load(Config.discover())
out.append(f"  video_references = {cfg.comfyui.video_references}")

# and where the check lives
out.append("")
out.append("=== 判失败的位置 ===")
v = Path(r"E:\dramakit\dramakit\pipeline\visual.py").read_text(encoding="utf-8")
i = v.index("def _wait_for_still")
out.append(v[i:i + 900])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\rooms.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
