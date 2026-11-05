"""Tell the console which lane is doing what.

The run has three lanes - the writing chain, the side work beside it
and the drawing - and the person watching wants to know what each one
is up to, not only what the whole run is doing.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\pipeline\runner.py")
text = PATH.read_text(encoding="utf-8")

old = '''            def _write_lane():
                try:
                    for name in chain:
                        if ctx.stopped:
                            break
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if name == "script":
                            script_done.set()
                        if _stop_if_wanted(name):
                            break
                finally:
                    # the side lane waits for the script, and the drawer's
                    # last pass waits for both lanes
                    script_done.set()
                    side_done.wait()
                    writes_done.set()

            def _side_lane():
                try:
                    # the voice and the music need the script and nothing
                    # else, so they start as soon as it is written
                    script_done.wait()
                    for name in side:
                        if ctx.stopped:
                            break
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if _stop_if_wanted(name):
                            break
                finally:
                    side_done.set()
'''

new = '''            def _write_lane():
                try:
                    for name in chain:
                        if ctx.stopped:
                            break
                        _lane(ctx, "写作", name)
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if name == "script":
                            script_done.set()
                        if _stop_if_wanted(name):
                            break
                finally:
                    # the side lane waits for the script, and the drawer's
                    # last pass waits for both lanes
                    script_done.set()
                    _lane(ctx, "写作", "")
                    side_done.wait()
                    writes_done.set()

            def _side_lane():
                try:
                    # the voice and the music need the script and nothing
                    # else, so they start as soon as it is written
                    script_done.wait()
                    for name in side:
                        if ctx.stopped:
                            break
                        _lane(ctx, "旁路", name)
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if _stop_if_wanted(name):
                            break
                finally:
                    _lane(ctx, "旁路", "")
                    side_done.set()
'''

assert old in text, "找不到那两条道"
text = text.replace(old, new, 1)

old_draw = '''            def _draw_lane():
                try:
                    _draw_until_done(ctx, writes_done, results, cfg)
                finally:
                    # the finisher waits for this: an episode can only be
                    # made once its shots are all drawn
                    drawing_done.set()
'''
new_draw = '''            def _draw_lane():
                try:
                    _lane(ctx, "绘制", "visual")
                    _draw_until_done(ctx, writes_done, results, cfg)
                finally:
                    _lane(ctx, "绘制", "")
                    # the finisher waits for this: an episode can only be
                    # made once its shots are all drawn
                    drawing_done.set()
'''
assert old_draw in text, "找不到画的那条道"
text = text.replace(old_draw, new_draw, 1)

# the helper
helper = '''

def _lane(ctx, lane: str, stage: str) -> None:
    """Say which stage a lane is working on, for the console."""
    try:
        from . import progress as _progress
        prog = _progress.attach(ctx)
        if stage:
            prog.lane(lane, stage)
        else:
            prog.lane_done(lane)
    except Exception:  # noqa: BLE001
        pass

'''
marker = "\ndef _stage_fn(name: str) -> Optional[Callable]:"
assert marker in text, "找不到插入点"
text = text.replace(marker, helper + "\ndef _stage_fn(name: str) -> Optional[Callable]:", 1)

PATH.write_text(text, encoding="utf-8")
print("改好了")
