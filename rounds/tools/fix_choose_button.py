"""The button that does nothing: a Set handed to slice.call.

chooseChapters turned the picked chapters into an array with
[].slice.call(set) - which throws "incompatible receiver" the moment it
sees a Set, so the function died on its first line and the button did
nothing at all.  Array.from is what turns a Set into an array.

And the episode count is gone.  The field was written to the project and
never read by anything: segment sizes the episodes from the text itself,
so asking the user for a number was a question the system already knew
the answer to.  The button now says what it actually does.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

old = """  const chosen = [].slice.call(_chapChosenSet());
  const want = Number((document.getElementById("epWanted")||{}).value || 0);
  await postJSON("/api/chapters/choose",{project:slug,chosen:chosen,episodes_wanted:want});
  toast("已选 "+chosen.length+" 章，按 "+want+" 集生成","",2000);
  const st = ["segment","script","storyboard"];
  await postJSON("/api/run",{project:slug,stages:st});
  toast("剧本与分镜开始…","",2600);"""

new = """  const chosen = Array.from(_chapChosenSet());
  if(!chosen.length){ toast("先勾选要做的章节","err"); return; }
  const r = await postJSON("/api/chapters/choose",{project:slug,chosen:chosen});
  if(!r || !r.ok){ toast("保存选章失败："+esc((r&&r.error)||"未知错误"),"err"); return; }
  toast("已选 "+chosen.length+" 章，开始分集与剧本…","",2200);
  const run = await postJSON("/api/run",{project:slug,
    stages:["segment","script","storyboard"]});
  if(!run || !run.ok){ toast("启动失败："+esc((run&&run.error)||"未知错误"),"err"); return; }
  // follow the job so the user sees it finish, or sees why it did not
  pollJob(run.job, (res,j)=>{
    if(!j){ return; }                              // pollJob already said why
    if(j.status==="error"){ return; }
    toast("剧本与分镜完成","",2600);
    renderWorkbench();
  });"""

assert old in s, "chooseChapters 锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("index.html: chooseChapters 改用 Array.from，去掉集数，接上任务进度")
