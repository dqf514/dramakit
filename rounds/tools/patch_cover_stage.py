"""Put the cover into the run, right after the analysis.

The cover is made of what the analysis found - the title, the world,
the people - so it belongs there: it is ready before the first line of
dialogue exists.
"""
import pathlib

# ------------------------------------------------------------------ runner
PATH = pathlib.Path(r"E:\dramakit\dramakit\pipeline\runner.py")
text = PATH.read_text(encoding="utf-8")

old_order = '''ORDER = ["ingest", "analyze", "character", "segment", "script", "storyboard",
         "promptgen", "voice", "visual", "lipsync", "subtitle", "music",
         "precheck", "compose", "qc"]'''
new_order = '''ORDER = ["ingest", "analyze", "cover", "character", "segment", "script",
         "storyboard", "promptgen", "voice", "visual", "lipsync", "subtitle",
         "music", "precheck", "compose", "qc"]'''
assert old_order in text, "找不到 ORDER"
text = text.replace(old_order, new_order, 1)

old_setup = 'SETUP = ("ingest", "analyze", "character", "segment")'
new_setup = 'SETUP = ("ingest", "analyze", "cover", "character", "segment")'
assert old_setup in text, "找不到 SETUP"
text = text.replace(old_setup, new_setup, 1)

old_fn = '''        "ingest": None,  # handled specially (needs source_file)
        "analyze": analyze.run,'''
new_fn = '''        "ingest": None,  # handled specially (needs source_file)
        "analyze": analyze.run,
        "cover": cover.run,'''
assert old_fn in text, "找不到阶段表"
text = text.replace(old_fn, new_fn, 1)

old_imp = "from . import (analyze, character, compose, ingest, lipsync, music_stage,"
new_imp = "from . import (analyze, character, compose, cover, ingest, lipsync, music_stage,"
assert old_imp in text, "找不到 import"
text = text.replace(old_imp, new_imp, 1)

PATH.write_text(text, encoding="utf-8")
print("runner 改好了")

# ------------------------------------------------------------------- init
PATH = pathlib.Path(r"E:\dramakit\dramakit\pipeline\__init__.py")
text = PATH.read_text(encoding="utf-8")
if "cover" not in text.split("\n")[2]:
    text = text.replace(
        "from . import (analyze, character, compose, ingest, lipsync, music_stage,",
        "from . import (analyze, character, compose, cover, ingest, lipsync,\n"
        "               music_stage,", 1)
    text = text.replace('"ingest", "analyze", "character", "segment", "script",',
                        '"ingest", "analyze", "cover", "character", "segment",\n    "script",', 1)
    PATH.write_text(text, encoding="utf-8")
    print("pipeline/__init__ 改好了")
