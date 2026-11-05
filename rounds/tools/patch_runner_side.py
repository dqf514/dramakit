"""Let the voice and the music run beside the storyboard.

The chain script -> storyboard -> promptgen has to be in order: each
stage writes what the next one reads.  The voice and the music need
the script and nothing else, so they do not wait for the shots - they
are made while the storyboard is still being written.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\pipeline\runner.py")
text = PATH.read_text(encoding="utf-8")

# 1. the new constant, next to the other lane definitions
old_const = 'WRITES = ("script", "storyboard", "promptgen", "voice", "music")'
new_const = (
    'WRITES = ("script", "storyboard", "promptgen", "voice", "music")\n'
    '# The stages that only need the script: the voice and the music do not\n'
    '# wait for the storyboard, so they are made beside it.\n'
    'SIDE_WRITES = ("voice", "music")'
)
assert old_const in text, "找不到 WRITES"
text = text.replace(old_const, new_const, 1)

# 2. the write lane
old_lane = '''        writes = _wanted(WRITES)
        draws = _wanted(DRAWS)

        # ---- the lanes that do not have to wait for each other -------
        if writes and draws:
            log.info("── 两道并行：写作 %s / 绘制 %s ──", writes, draws)
            writes_done = threading.Event()
            drawing_done = threading.Event()
            results_lock = threading.Lock()

            def _write_lane():
                try:
                    for name in writes:
                        if ctx.stopped:
                            break
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if _stop_if_wanted(name):
                            break
                finally:
                    # the drawer's last pass is gated on this, so it has to
                    # be set even when the lane failed or was stopped
                    writes_done.set()
'''

new_lane = '''        writes = _wanted(WRITES)
        draws = _wanted(DRAWS)
        # The chain: each stage writes what the next one reads.  The rest
        # only need the script, so they do not wait for the storyboard or
        # the prompts - the voice and the music are made while the shots
        # are still being written.
        chain = [s for s in writes if s not in SIDE_WRITES]
        side = [s for s in writes if s in SIDE_WRITES]

        # ---- the lanes that do not have to wait for each other -------
        if writes and draws:
            log.info("── 两道并行：写作 %s / 绘制 %s ──", writes, draws)
            writes_done = threading.Event()
            drawing_done = threading.Event()
            script_done = threading.Event()
            side_done = threading.Event()
            results_lock = threading.Lock()

            def _write_lane():
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

assert old_lane in text, "找不到写的那条道"
text = text.replace(old_lane, new_lane, 1)

# 3. the side lane needs a place in the pool
old_pool = '''            with ThreadPoolExecutor(max_workers=3) as pool:
                wfut = pool.submit(_write_lane)
                dfut = pool.submit(_draw_lane)'''
new_pool = '''            with ThreadPoolExecutor(max_workers=4) as pool:
                wfut = pool.submit(_write_lane)
                sfut = pool.submit(_side_lane)
                dfut = pool.submit(_draw_lane)'''
assert old_pool in text, "找不到线程池"
text = text.replace(old_pool, new_pool, 1)

old_wait = '''                wfut.result()
                dfut.result()
                ffut.result()'''
new_wait = '''                wfut.result()
                sfut.result()
                dfut.result()
                ffut.result()'''
assert old_wait in text, "找不到等待"
text = text.replace(old_wait, new_wait, 1)

# 4. the path with no drawing: the side lane still has to run
old_else = '''        else:
            for name in writes + draws:
                if ctx.stopped:
                    break
                season_obj = _run_stage(ctx, name, None, season_obj,
                                        results, cfg) or season_obj
                if _stop_if_wanted(name):
                    return _finish(ctx, season_obj, stages, results)'''
new_else = '''        else:
            for name in chain + draws:
                if ctx.stopped:
                    break
                season_obj = _run_stage(ctx, name, None, season_obj,
                                        results, cfg) or season_obj
                if _stop_if_wanted(name):
                    return _finish(ctx, season_obj, stages, results)
            for name in side:
                if ctx.stopped:
                    break
                season_obj = _run_stage(ctx, name, None, season_obj,
                                        results, cfg) or season_obj
                if _stop_if_wanted(name):
                    return _finish(ctx, season_obj, stages, results)'''
assert old_else in text, "找不到不并行的分支"
text = text.replace(old_else, new_else, 1)

PATH.write_text(text, encoding="utf-8")
print("改好了")
