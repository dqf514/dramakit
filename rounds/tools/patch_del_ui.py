"""Delete a project from the sidebar, with a warning that reads first."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

# the title line of a project card, exactly as it is written
old = '<div class="pn">${esc(p.title)}</div>'
new = ('<div class="pn">${esc(p.title)}'
       '<span class="mini" title="删除项目" '
       'style="float:right;cursor:pointer;opacity:.5;margin-left:6px" '
       "onclick=\"event.stopPropagation();deleteProject('${esc(p.slug)}')\">×</span></div>")
if old in s:
    s = s.replace(old, new, 1)
    print("index.html: 卡片上加了 ×")
else:
    print("index.html: 卡片标题模板对不上")

if "async function deleteProject" not in s:
    js = '''
<script>
// delete a project: say what it takes away, and ask twice
async function deleteProject(slug){
  const p = (S.projects||[]).find(x=>x.slug===slug);
  const who = (p && p.title) || slug;
  const what = p ? ((p.episodes||0)+" 集、"+(p.shots||0)+" 个镜头、"+(p.characters||0)+" 个角色") : "";
  if(!confirm("确定删除项目「"+who+"」？\\n\\n里面是："+what+"\\n\\n删除后会先移到 projects/_trash/，不会立即销毁。")) return;
  const typed = prompt("再输入项目名「"+who+"」确认删除：");
  if(typed===null) return;
  if(typed.trim() !== who && typed.trim() !== slug){
    toast("名字对不上，没有删除","",2600); return;
  }
  const r = await postJSON("/api/projects/delete",{project:slug});
  if(!r || !r.ok){ toast((r&&r.error)||"删除失败","",2600); return; }
  toast("已移到 projects/_trash/","",2600);
  S.projects = (S.projects||[]).filter(x=>x.slug!==slug);
  renderProjects();
  if(S.current===slug){ S.current = ""; S.detail = null; }
}
</script>
'''
    j = s.find("</body>")
    assert j > 0, "没找到 </body>"
    s = s[:j] + js + "\n" + s[j:]
    print("index.html: 加了删除函数")

p.write_text(s, encoding="utf-8")
print("index.html: 侧栏删除做好了")
