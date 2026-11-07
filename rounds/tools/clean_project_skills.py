"""The projects still name skills that are gone.

The theory skills were removed, and the projects that had them on
their list kept the names - so every run warned about a skill that
cannot be loaded, and the stage wrote with less than it should.

This takes the names that no longer exist off every project's list.
"""
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.skills import catalog as skillcat  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

ROOT = pathlib.Path(r"E:\dramakit\projects")
have = {s["name"] for s in skillcat.catalog()}
print("  现在的技能：%d 个" % len(have))

for d in sorted(ROOT.iterdir()):
    if not d.is_dir() or d.name.startswith("_"):
        continue
    try:
        store = ProjectStore.open(str(d))
        proj = store.load()
    except Exception as e:  # noqa: BLE001
        print("  %s：打不开（%s）" % (d.name, str(e)[:60]))
        continue
    sel = proj.meta.skills or {}
    if not sel:
        continue
    changed = False
    for stage, names in list(sel.items()):
        keep = [n for n in names if n in have]
        if keep != names:
            changed = True
        if keep:
            sel[stage] = keep
        else:
            # an empty list means "the config's choice", so the key goes
            del sel[stage]
    if changed:
        proj.meta.skills = sel
        store.save(proj)
        print("  %s → %s" % (d.name, {k: v for k, v in sel.items()}))
    else:
        print("  %s：没动" % d.name)
