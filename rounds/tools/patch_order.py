"""The look, the skills and the toast, in the right order.

Three things went wrong together.  The toast that said the skills had
been changed was still on the screen when the toast that said the
settings had been saved came - so the page said the wrong thing about
what had just happened.  And the skills were written after the look,
so the answer to the look's save was still on its way when a box was
ticked - and the tick was written over by the answer to an earlier
write.

So: the look's save writes the skills first and the look second, the
note about the skills goes into the panel instead of into a toast, and
the saves stay in a line.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html")
text = PATH.read_text(encoding="utf-8")

# 1. the note goes into the panel, not into a toast
old = '''    toast("已按「"+esc(got.name)+"」换了一套技能，点保存一起写进去","ok",3600);'''
new = '''    const note=document.getElementById("skNote");
    if(note) note.textContent="按「"+esc(got.name)+"」换的一套，点保存一起写进去";'''
assert old in text, "没找到风格的提示"
text = text.replace(old, new, 1)

# 2. the panel has a place for that note
old = '''      <b>技能</b>
      <span class="muted" style="font-size:12px">勾上就存到本项目，下次跑流水线生效${esc(rec)}</span>
    </div>'''
new = '''      <b>技能</b>
      <span class="muted" style="font-size:12px">勾上就存到本项目，下次跑流水线生效${esc(rec)}</span>
      <span class="muted" id="skNote" style="font-size:12px"></span>
    </div>'''
assert old in text, "没找到技能面板的头"
text = text.replace(old, new, 1)

# 3. the look saves the skills first, and the look second
old = '''  const r=await postJSON("/api/project/look",body);
  if(!r||!r.ok) return toast("保存失败："+esc((r&&r.error)||"未知错误"),"err");
  if(S.detail) S.detail.art_direction=r.art_direction;
  // the skills that came with the look are written with it
  if(SK&&SK.selection){
    const sr=await saveSkills(SK.selection);
    if(sr&&sr.ok){
      SK.selection=sr.selection||SK.selection;
      SK.costs=sr.costs||SK.costs;
    }
  }'''
new = '''  // the skills that came with the look are written first, so that the
  // answer to the look's save is the last thing on the wire - a box
  // ticked a moment later must not be written over by an earlier write
  if(SK&&SK.selection){
    const sr=await saveSkills(SK.selection);
    if(sr&&sr.ok){
      SK.selection=sr.selection||SK.selection;
      SK.costs=sr.costs||SK.costs;
    }
  }
  const r=await postJSON("/api/project/look",body);
  if(!r||!r.ok) return toast("保存失败："+esc((r&&r.error)||"未知错误"),"err");
  if(S.detail) S.detail.art_direction=r.art_direction;'''
assert old in text, "没找到保存设置"
text = text.replace(old, new, 1)

PATH.write_text(text, encoding="utf-8")
print("顺序和提示都改好了")
