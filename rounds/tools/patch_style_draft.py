"""The look brings its skills with it, and they are written with it.

The look was changing the skills by writing them at once, and a box
ticked a second later was written over by the answer to the first
write - so a choice made by hand was lost.  Two writes for one thing,
and the slower one won.

Now the look changes the skills on the page, and the 保存 button writes
the look and the skills together.  A box ticked by hand is still saved
at once, and it carries the linked skills of that stage with it, so
nothing is lost either way.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html")
text = PATH.read_text(encoding="utf-8")

# 1. the look changes the skills on the page, not on the server
old = """    const r=await saveSkills(clean);
    if(!r||!r.ok){ toast("技能保存失败","err"); return; }
    SK.selection=r.selection||SK.selection;
    SK.costs=r.costs||SK.costs;
    SK.recommended=false;
    // the boxes are updated where they are: the page is not redrawn, so
    // the thing that was being set is not taken away under the pointer
    syncSkillBoxes();
    for(const stage of ["analyze","script","storyboard","promptgen"]){
      const head=document.getElementById("skhead-"+stage);
      if(!head) continue;
      const n=(SK.selection[stage]||[]).length;
      const c=head.querySelector(".muted");
      if(c) c.textContent=n+" 个 · "+fmtChars(SK.costs[stage]||0);
    }
    toast("已按「"+esc(got.name)+"」换了一套技能，可以再改","ok",3200);"""
new = """    // on the page, not on the server: the 保存 button writes the look
    // and the skills together, so a box ticked in between is not written
    // over by the answer to an earlier write
    SK.selection=clean;
    SK.recommended=false;
    syncSkillBoxes();
    for(const stage of ["analyze","script","storyboard","promptgen"]){
      const head=document.getElementById("skhead-"+stage);
      if(!head) continue;
      const n=(SK.selection[stage]||[]).length;
      const c=head.querySelector(".muted");
      if(c) c.textContent=n+" 个 · "+fmtChars(skillCost(stage,clean));
    }
    toast("已按「"+esc(got.name)+"」换了一套技能，点保存一起写进去","ok",3600);"""
assert old in text, "没找到风格联动"
text = text.replace(old, new, 1)

# 2. the cost of a stage, for the page
old = """let skillSaveQueue=Promise.resolve();"""
new = """function skillCost(stage,selection){
  const sel=selection||((SK&&SK.selection)||{});
  const byName={};
  ((SK&&SK.skills)||[]).forEach(x=>{ byName[x.name]=x.chars||0; });
  let n=0;
  (sel[stage]||[]).forEach(x=>{ n+=byName[x]||0; });
  return n;
}
let skillSaveQueue=Promise.resolve();"""
assert old in text, "没找到队列"
text = text.replace(old, new, 1)

# 3. saving the look saves the skills that came with it
old = """  if(S.detail) S.detail.art_direction=r.art_direction;
  // it is on the project now; the card shows the project, not a draft
  S.lookDraft=null;
  toast("已保存 · 画幅与风格会贯穿角色制图与视频提示词","ok",3600);"""
new = """  if(S.detail) S.detail.art_direction=r.art_direction;
  // the skills that came with the look are written with it
  if(SK&&SK.selection){
    const sr=await saveSkills(SK.selection);
    if(sr&&sr.ok){
      SK.selection=sr.selection||SK.selection;
      SK.costs=sr.costs||SK.costs;
    }
  }
  // it is on the project now; the card shows the project, not a draft
  S.lookDraft=null;
  toast("已保存 · 画幅与风格会贯穿角色制图与视频提示词","ok",3600);"""
assert old in text, "没找到保存设置"
text = text.replace(old, new, 1)

PATH.write_text(text, encoding="utf-8")
print("风格联动改成跟设置一起保存")
