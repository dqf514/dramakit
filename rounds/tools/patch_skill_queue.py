"""The skill saves take their turn.

Two things write the project's skills: the look, which brings its own
with it, and the boxes, which are ticked by hand.  If the two write at
the same time, the slower one wins and the other's change is lost - so
the saves are put in a line and each one waits for the last.

The same queue is what makes the look's skills and a ticked box agree:
the box that was ticked after the look changed is saved after it, so
the ticked one is what the server holds.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html")
text = PATH.read_text(encoding="utf-8")

# 1. the queue
old = """// every box shows what the server now holds
function syncSkillBoxes(){"""
new = """// The skill saves, in a line.  The look brings its own skills and the
// boxes are ticked by hand, and the two must not write over each other.
let skillSaveQueue=Promise.resolve();
function saveSkills(selection){
  skillSaveQueue=skillSaveQueue.then(()=>
    postJSON("/api/skills/save",{project:S.current,selection}))
    .catch(()=>null);
  return skillSaveQueue;
}
// every box shows what the server now holds
function syncSkillBoxes(){"""
assert old in text, "没找到 syncSkillBoxes"
text = text.replace(old, new, 1)

# 2. a ticked box goes through the queue
old = """    postJSON("/api/skills/save",{project:S.current,selection:{[stage]:list}}).then(r=>{
      if(!r||!r.ok){ toast("技能保存失败","err"); return; }"""
new = """    saveSkills({[stage]:list}).then(r=>{
      if(!r||!r.ok){ toast("技能保存失败","err"); return; }"""
assert old in text, "没找到勾选保存"
text = text.replace(old, new, 1)

# 3. and so does the look
old = """    const r=await postJSON("/api/skills/save",{project:S.current,selection:clean});
    if(!r||!r.ok){ toast("技能保存失败","err"); return; }"""
new = """    const r=await saveSkills(clean);
    if(!r||!r.ok){ toast("技能保存失败","err"); return; }"""
assert old in text, "没找到风格联动保存"
text = text.replace(old, new, 1)

PATH.write_text(text, encoding="utf-8")
print("保存排队了")
