"""The casting does not have to stand in front of the writing.

The character stage is the heaviest thing on the card: four reference
pictures for every character, plus one voice sample each.  The
screenplay and the storyboard only need the names and the text of the
cast - the anchors and the pictures are wanted by the prompt writer and
by the picture machine, not by the writing.

So the casting is put beside the writing instead of in front of it, and
the one stage that waits for it is the prompt writer, which puts the
anchors into the prompts.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\pipeline\runner.py")
text = PATH.read_text(encoding="utf-8")

old = '''SETUP = ("ingest", "analyze", "cover", "character", "segment")'''
new = '''SETUP = ("ingest", "analyze", "cover")
# The casting is the heaviest thing on the card - four reference pictures
# for every character and a voice sample each - and the writing only
# needs the names and the text of the cast.  So the casting runs beside
# the writing instead of in front of it, and the one stage that waits
# for it is the prompt writer, which puts the anchors into the prompts.
CASTING = ("character",)'''
assert old in text, "找不到 SETUP"
text = text.replace(old, new, 1)

old_writes = 'WRITES = ("script", "storyboard", "promptgen", "voice", "music")'
new_writes = 'WRITES = ("segment", "script", "storyboard", "promptgen", "voice", "music")'
assert old_writes in text, "找不到 WRITES"
text = text.replace(old_writes, new_writes, 1)

# the lanes
old_lanes = '''            writes_done = threading.Event()
            drawing_done = threading.Event()
            script_done = threading.Event()
            side_done = threading.Event()
            results_lock = threading.Lock()

            def _write_lane():
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
'''
new_lanes = '''            writes_done = threading.Event()
            drawing_done = threading.Event()
            script_done = threading.Event()
            side_done = threading.Event()
            cast_done = threading.Event()
            results_lock = threading.Lock()

            def _cast_lane():
                """The casting: the pictures of the cast and their voices."""
                try:
                    for name in casting:
                        if ctx.stopped:
                            break
                        _lane(ctx, "定妆", name)
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if _stop_if_wanted(name):
                            break
                finally:
                    cast_done.set()
                    _lane(ctx, "定妆", "")

            def _write_lane():
                try:
                    for name in chain:
                        if ctx.stopped:
                            break
                        if name == "promptgen":
                            # the prompts carry the characters' anchors, so
                            # this is the one stage that waits for the casting
                            cast_done.wait()
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
'''
assert old_lanes in text, "找不到那几条道"
text = text.replace(old_lanes, new_lanes, 1)

old_pool = '''            with ThreadPoolExecutor(max_workers=4) as pool:
                wfut = pool.submit(_write_lane)
                sfut = pool.submit(_side_lane)
                dfut = pool.submit(_draw_lane)'''
new_pool = '''            with ThreadPoolExecutor(max_workers=5) as pool:
                wfut = pool.submit(_write_lane)
                cfut = pool.submit(_cast_lane)
                sfut = pool.submit(_side_lane)
                dfut = pool.submit(_draw_lane)'''
assert old_pool in text, "找不到线程池"
text = text.replace(old_pool, new_pool, 1)

old_wait = '''                wfut.result()
                sfut.result()
                dfut.result()
                ffut.result()'''
new_wait = '''                wfut.result()
                cfut.result()
                sfut.result()
                dfut.result()
                ffut.result()'''
assert old_wait in text, "找不到等待"
text = text.replace(old_wait, new_wait, 1)

# the path with no drawing: the casting comes first, then the writing
old_else = '''        else:
            for name in chain + draws:
                if ctx.stopped:
                    break
                season_obj = _run_stage(ctx, name, None, season_obj,
                                        results, cfg) or season_obj
                if _stop_if_wanted(name):
                    return _finish(ctx, season_obj, stages, results)
            for name in side:'''
new_else = '''        else:
            for name in list(casting) + chain + draws:
                if ctx.stopped:
                    break
                season_obj = _run_stage(ctx, name, None, season_obj,
                                        results, cfg) or season_obj
                if _stop_if_wanted(name):
                    return _finish(ctx, season_obj, stages, results)
            for name in side:'''
assert old_else in text, "找不到不并行的分支"
text = text.replace(old_else, new_else, 1)

# the casting list
old_wanted = '''        writes = _wanted(WRITES)
        draws = _wanted(DRAWS)'''
new_wanted = '''        writes = _wanted(WRITES)
        draws = _wanted(DRAWS)
        casting = _wanted(CASTING)'''
assert old_wanted in text, "找不到 writes"
text = text.replace(old_wanted, new_wanted, 1)

PATH.write_text(text, encoding="utf-8")
print("runner 改好了")
