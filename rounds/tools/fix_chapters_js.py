"""The chapter picker needs its functions written into the page."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

if "async function chooseChapters" in s:
    print("index.html: 已经有了")
else:
    js = '''
<script>
// the chapter picker: the table of contents, and how many episodes
window.__chapters = [];
async function loadChapters(slug){
  const r = await postJSON("/api/catalog",{project:slug});
  if(!r || !r.ok) return;
  window.__chapters = r.chapters || [];
  const box = document.getElementById("chapterList");
  if(!box) return;
  box.innerHTML = window.__chapters.map((c,i)=>
    '<label style="display:flex;gap:8px;align-items:center;padding:3px 0">' +
      '<input type="checkbox" data-idx="' + c.index + '" checked> ' +
      '<b>' + (c.volume||'') + ' 第' + c.index + '章</b> ' + (c.title||'') + ' ' +
      '<span class="muted">' + Math.round(c.chars/1000) + 'k 字</span>' +
    '</label>').join("") || '<div class="muted">这本书没有切出章节</div>';
  const card = document.getElementById("guide-chapters");
  if(card) card.style.display = "";
}
async function chooseChapters(){
  const slug = window.__project;
  const boxes = [].slice.call(document.querySelectorAll("#chapterList input[type=checkbox]"));
  const chosen = boxes.filter(function(b){return b.checked;})
                      .map(function(b){return Number(b.dataset.idx);});
  const want = Number((document.getElementById("epWanted")||{}).value || 0);
  await postJSON("/api/chapters/choose",{project:slug,chosen:chosen,episodes_wanted:want});
  toast("已选 "+chosen.length+" 章，按 "+want+" 集生成","",2000);
  await postJSON("/api/run",{project:slug,stages:["segment","script","storyboard"]});
  toast("剧本与分镜开始…","",2600);
}
</script>
'''
    i = s.find("</body>")
    assert i > 0, "没找到 </body>"
    s = s[:i] + js + "\n" + s[i:]
    p.write_text(s, encoding="utf-8")
    print("index.html: 加了章节选择脚本")
