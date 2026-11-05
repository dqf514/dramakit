"""The prompts are saved as they are made, not after the whole batch.

A shot that has its prompt is a shot that does not have to be asked
about again.  If the run is stopped halfway, the shots that already
have their prompts keep them.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\pipeline\promptgen.py")
text = PATH.read_text(encoding="utf-8")

old = '''    def _one(job):
        shot, sc, visuals, flf, location_visual, need_img, need_h3, cont, dlg_map = job
        if need_img:
            _gen_image_prompt(ctx, pool.next(), shot, sc, visuals, flf,
                              location_visual, continuity=cont)
        if need_h3:
            _gen_h3_prompt(ctx, pool.next(), shot, sc, visuals, location_visual,
                           dlg_map.get(shot.id, []), continuity=cont)
'''

new = '''    made = 0
    save_lock = threading.Lock()

    def _one(job):
        nonlocal made
        shot, sc, visuals, flf, location_visual, need_img, need_h3, cont, dlg_map = job
        if need_img:
            _gen_image_prompt(ctx, pool.next(), shot, sc, visuals, flf,
                              location_visual, continuity=cont)
        if need_h3:
            _gen_h3_prompt(ctx, pool.next(), shot, sc, visuals, location_visual,
                           dlg_map.get(shot.id, []), continuity=cont)
        # the shot has its prompt now, and it keeps it: a run that is
        # stopped halfway does not ask for the same prompt twice
        with save_lock:
            made += 1
            every = made % 5 == 0
        if every:
            ctx.save()
'''

assert old in text, "找不到 promptgen 的那一段"
text = text.replace(old, new, 1)

old_import = "from concurrent.futures import ThreadPoolExecutor"
new_import = "import threading\nfrom concurrent.futures import ThreadPoolExecutor"
if old_import in text and "\nimport threading\n" not in text:
    text = text.replace(old_import, new_import, 1)

PATH.write_text(text, encoding="utf-8")
print("promptgen 改好了")
