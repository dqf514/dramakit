"""The chapter picker: the table of contents, and how many episodes.

The chapters are listed with their volumes and their lengths; the user
picks the ones the drama is made from and says how many episodes to cut
them into.  The pipeline starts when the pick is made.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

if "guide-chapters" not in s:
    card = '''<div class="card" id="guide-chapters" style="display:none">
      <h3>选章节 · 生成集数</h3>
      <div id="chapterList" style="max-height:300px;overflow:auto;margin:10px 0"></div>
      <div style="display:flex;gap:12px;align-items:center;margin-top:8px">
        <label>生成几集：</label>
        <input type="number" id="epWanted" value="3" min="1" max="50" style="width:70px">
        <button class="btn go" onclick="chooseChapters()">开始流水线</button>
      </div>
    </div>
'''
    i = s.find('id="guide-new"')
    j = s.find("</div>\n", s.find("文件会复制进项", i))
    if j < 0:
        j = s.find("</div>", i)
    k = s.find("</div>", j + 1)
    if k > 0:
        s = s[:k + 6] + card + s[k + 6:]
        print("index.html: 加了章节选择卡")

if "chooseChapters" not in s:
    js = '''
<script>
// the chapter picker: the table of contents, and how many episodes
window.__chapters = [];
async function loadChapters(slug){
  const r = await getJSON("/api/catalog?project="+encodeURIComponent(slug));
  if(!r || !r.ok) return;
  window.__chapters = r.chapters || [];
  const box = document.getElementById("chapterList");
  if(!box) return;
  box.innerHTML = window.__chapters.map((c,i)=>
    `<label style="display:flex;gap:8px;align-items:center;padding:3px 0">
       <input type="checkbox" data-idx="${c.index}" checked>
       <b>${c.volume||""} 第${c.index}章</b> ${esc(c.title||"")}
       <span class="muted">${Math.round(c.chars/1000)}k 字</span>
     </label>`).join("") || '<div class="muted">这本书没有切出章节</div>';
  const card = document.getElementById("guide-chapters");
  if(card) card.style.display = "";
}
async function chooseChapters(){
  const slug = window.__project;
  const boxes = [...document.querySelectorAll("#chapterList input[type=checkbox]")];
  const chosen = boxes.filter(b=>b.checked).map(b=>Number(b.dataset.idx));
  const want = Number(document.getElementById("epWanted")?.value||0);
  await postJSON("/api/chapters/choose",{project:slug,chosen,episodes_wanted:want});
  toast("已选 "+chosen.length+" 章，按 "+want+" 集生成","",2000);
  // and start the pipeline at the stages that turn chapters into episodes
  await postJSON("/api/run",{project:slug,stages:["segment","script","storyboard"]});
  toast("剧本与分镜开始…","",2600);
}
</script>
'''
    s = s.replace("</body>", js + "\n</body>", 1)
    print("index.html: 加了章节选择脚本")

p.write_text(s, encoding="utf-8")
print("index.html: 章节选择做好了")
