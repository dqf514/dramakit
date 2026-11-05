"""The book, in a sentence, beside its cover.

The cover and the title say what the drama is called.  A person who has
just opened the project has no idea what it is about, and the synopsis
is the one sentence that says it - and it is also what the skill
recommendation is read from, so it is worth having on the page.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html")
text = PATH.read_text(encoding="utf-8")

old = '''              <h1 class="ht">${esc(d.meta.title||d.meta.name)}</h1>
              <div class="hm">${esc(d.art_direction.genre||"")} · ${esc(d.art_direction.style||"")} · ${esc(d.art_direction.aspect_ratio||"9:16")}</div>'''
new = '''              <h1 class="ht">${esc(d.meta.title||d.meta.name)}</h1>
              <div class="hm">${esc(d.art_direction.genre||"")} · ${esc(d.art_direction.style||"")} · ${esc(d.art_direction.aspect_ratio||"9:16")}</div>
              ${(d.meta.synopsis||d.season_synopsis||"")?`<div class="hsyn" title="${attr(d.meta.synopsis||d.season_synopsis||"")}">${esc(d.meta.synopsis||d.season_synopsis||"")}</div>`:""}'''
assert old in text, "没找到标题"
text = text.replace(old, new, 1)

# the style
old_css = "  .hero .cover{width:96px;height:170px;flex:0 0 auto;border-radius:7px;overflow:hidden;"
new_css = ("  .hero .hsyn{margin-top:5px;font-size:12.5px;line-height:1.45;color:var(--fg2);\n"
           "    max-width:52ch;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;\n"
           "    overflow:hidden}\n"
           "  .hero .cover{width:96px;height:170px;flex:0 0 auto;border-radius:7px;overflow:hidden;")
assert old_css in text, "没找到封面的样式"
text = text.replace(old_css, new_css, 1)

PATH.write_text(text, encoding="utf-8")
print("简介加上了")
