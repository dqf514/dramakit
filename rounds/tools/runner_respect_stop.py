"""A stop lands between stages, and is recorded as a refusal, not a fault.

run_pipeline marked every non-completion a failure, so a stage that was
asked to stop would have been written up as broken - and the next run
would have treated it as work that errored rather than work that was
refused. It also never asked whether anyone still wanted to continue, so
a stop raised inside a stage was the only kind that could happen.

The loop now asks before each stage, and RunStopped is caught separately:
the stage keeps whatever it had finished, and is marked interrupted.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\runner.py")
s = p.read_text(encoding="utf-8", errors="replace")

if "RunStopped" in s:
    print("runner.py: 已有停止处理，跳过")
    raise SystemExit(0)

# import the exception
old_imp = "from .base import Context"
new_imp = "from .base import Context, RunStopped"
assert old_imp in s, "base 导入锚点没找到"
s = s.replace(old_imp, new_imp, 1)

# ask before each stage
old_loop = '''    for name in stages:
        if name not in cfg.pipeline.stages_enabled and stages == cfg.pipeline.stages_enabled:
            continue
        log.info("── 阶段 [%s] 开始 ──", name)'''
new_loop = '''    for name in stages:
        # Ask before starting anything new. A stage that was already asked
        # to stop raises inside its own loops; this is the other half, so
        # a stop between stages does not begin the next one.
        if ctx.stopped:
            log.info("── 已停止，未开始 [%s] ──", name)
            ctx.project.stage_status[name] = Status.INTERRUPTED
            if season_obj is not None:
                season_obj.stage_status[name] = Status.INTERRUPTED
            results[name] = {"interrupted": True}
            break
        if name not in cfg.pipeline.stages_enabled and stages == cfg.pipeline.stages_enabled:
            continue
        log.info("── 阶段 [%s] 开始 ──", name)'''
assert old_loop in s, "阶段循环锚点没找到"
s = s.replace(old_loop, new_loop, 1)

# catch a refusal separately from a failure
old_exc = '''        except Exception as e:  # noqa: BLE001
            ctx.project.stage_status[name] = Status.FAILED
            if season_obj is not None:
                season_obj.stage_status[name] = Status.FAILED
            ctx.save()
            log.error("阶段 [%s] 失败: %s", name, e)'''
new_exc = '''        except RunStopped:
            # a refusal, not a fault: whatever the stage finished stays
            # finished, and the stage is marked interrupted so the next
            # run knows to begin here rather than at the start
            ctx.project.stage_status[name] = Status.INTERRUPTED
            if season_obj is not None:
                season_obj.stage_status[name] = Status.INTERRUPTED
            ctx.save()
            log.info("── 阶段 [%s] 已停止 ──", name)
            results[name] = {"interrupted": True}
            break
        except Exception as e:  # noqa: BLE001
            ctx.project.stage_status[name] = Status.FAILED
            if season_obj is not None:
                season_obj.stage_status[name] = Status.FAILED
            ctx.save()
            log.error("阶段 [%s] 失败: %s", name, e)'''
assert old_exc in s, "异常处理锚点没找到"
s = s.replace(old_exc, new_exc, 1)

# a season that was interrupted is neither done nor failed
old_season = '''        done = all(season_obj.stage_status.get(n) == Status.DONE
                   for n in stages if n in season_obj.stage_status)
        season_obj.status = Status.DONE if done else Status.FAILED'''
new_season = '''        vals = [season_obj.stage_status.get(n) for n in stages
                if n in season_obj.stage_status]
        if any(v == Status.INTERRUPTED for v in vals):
            season_obj.status = Status.INTERRUPTED
        else:
            done = all(v == Status.DONE for v in vals)
            season_obj.status = Status.DONE if done else Status.FAILED'''
assert old_season in s, "季状态锚点没找到"
s = s.replace(old_season, new_season, 1)

p.write_text(s, encoding="utf-8")
print("runner.py: 阶段间会问要不要停，中断记成 INTERRUPTED 而不是 FAILED")
