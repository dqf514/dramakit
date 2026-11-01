"""The browser's half: send the file, see the table of contents, pick.

The console could take a path, which is a fine thing for a machine that
shares a disk with the pipeline and a poor thing for a browser.  So the
browser sends the file - it lands in the project's source folder - the
book is cut into volumes and chapters, and the console shows the table of
contents with the chapters to pick from and the number of episodes to cut
them into.

Everything the user has to do is on one screen: the file, the chapters,
the number, the button.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

# --------------------------------------------------------------------------- #
# 1. a file picker beside the path field
# --------------------------------------------------------------------------- #
if 'id="gFilePicker"' not in s:
    old = """<label class="fl">小说 / 剧本文件（可留空，稍后导入）</label><input class="f" id="gSource" placeholder="D:/novels/战神归来.txt"></div>"""
    new = """<label class="fl">小说 / 剧本文件</label><input class="f" id="gSource" placeholder="选本地文件，或填服务器上的路径"><input type="file" id="gFilePicker" accept=".txt,.md" style="display:none"><button type="button" class="btn ghost" onclick="document.getElementById('gFilePicker').click()">选择本地文件</button></div>"""
    assert old in s, "路径输入框锚点没找到"
    s = s.replace(old, new, 1)
    print("index.html: 加了文件选择")

# --------------------------------------------------------------------------- #
# 2. the create button sends the file when one is picked
# --------------------------------------------------------------------------- #
if 'api/upload' not in s:
    old = """const r=await postJSON("/api/new",{name,source});"""
    assert old in s, "创建按钮锚点没找到"
    new = """const picked=document.getElementById("gFilePicker")?.files?.[0];
let r;
if(picked){
  const text=await picked.text();
  toast("上传并切分章节…","",2000);
  r=await postJSON("/api/upload",{name,file:picked.name,text});
  if(r&&r.catalog_error) r.error=r.catalog_error;
}else{
  r=await postJSON("/api/new",{name,source});
}"""
    s = s.replace(old, new, 1)
    print("index.html: 创建时会传文件")

p.write_text(s, encoding="utf-8")
print("index.html: 新建项目可以传文件了")
