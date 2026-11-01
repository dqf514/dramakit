"""The seasons panel shows what a season produced, not just its name.

The route hands back the episode range a season produced, and the panel
ignored it - so a project made before seasons existed showed up as
「（旧数据）」with a bare episode count, which tells the user nothing about
which part of the book that was. The row now prefers the episodes, then
the chapters, and only says what it cannot know.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8")

old = """    const span = (se.chapters&&se.chapters.length)
      ? ("第" + Math.min.apply(null,se.chapters) + "~" +
         Math.max.apply(null,se.chapters) + "章") : "（旧数据）";"""
new = """    // what this season covered: the episodes it produced says more than
    // the chapters it read, and a season made before seasons existed has
    // only the episodes.
    let span = "";
    if(se.episode_range && se.episode_range.length===2){
      span = "第" + se.episode_range[0] + "~" + se.episode_range[1] + "集";
    } else if(se.chapters && se.chapters.length){
      span = "第" + Math.min.apply(null,se.chapters) + "~" +
             Math.max.apply(null,se.chapters) + "章";
    } else {
      span = "来路不明";
    }"""
assert old in s, "season span anchor not found"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("index.html: seasons panel shows the episode range a season produced")
