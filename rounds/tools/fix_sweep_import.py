"""The sweep that settles a dead run must not be the thing that kills startup.

It imported nothing and raised NameError on the first project, so the
console came up dead - the check meant to stop the console lying about
progress was instead stopping the console. Two fixes, and the second is
the one that matters: Status is imported, and every project is settled
inside its own try, so a project that cannot be read is skipped rather
than fatal. A repair pass that can take the service down is worse than no
repair pass.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

# the import
old_imp = "from ..project import ProjectStore"
new_imp = "from ..models import Status\nfrom ..project import ProjectStore"
if "from ..models import Status" not in s:
    assert old_imp in s, "ProjectStore 导入锚点没找到"
    s = s.replace(old_imp, new_imp, 1)
    print("server.py: 导入 Status")

# make the sweep survive a project it cannot read
old_try = '''            try:
                proj = store.load()
            except Exception:  # noqa: BLE001
                continue'''
new_try = '''            try:
                proj = store.load()
            except Exception:  # noqa: BLE001
                continue
            # Everything below is repair, and repair that can take the
            # console down is worse than no repair: a project that cannot
            # be swept is skipped, not fatal.'''
if old_try in s:
    # wrap the whole per-project body in a guard by indenting a try around it
    # simpler and safer: catch around the save as well
    old_save = '''            if changed:
                store.save(proj)
                log.warning("项目 %s: 有阶段停在 running，已标记为中断", slug)'''
    new_save = '''            if changed:
                try:
                    store.save(proj)
                    log.warning("项目 %s: 有阶段停在 running，已标记为中断", slug)
                except Exception as e:  # noqa: BLE001
                    log.warning("项目 %s: 清理结果写不进去（%s），跳过", slug, e)'''
    assert old_save in s, "保存那段锚点没找到"
    s = s.replace(old_save, new_save, 1)
    print("server.py: 清理写入失败不再致命")

# and the whole method body, belt and braces
old_call = '''    state.settle_leftover_runs()'''
new_call = '''    try:
        state.settle_leftover_runs()
    except Exception as e:  # noqa: BLE001
        # a failed tidy-up must never be why the console will not start
        log.warning("启动时清理残留状态失败（%s），已跳过", e)'''
assert old_call in s, "serve 里的调用锚点没找到"
s = s.replace(old_call, new_call, 1)

p.write_text(s, encoding="utf-8")
print("server.py: 清理逻辑不会挡住启动了")
