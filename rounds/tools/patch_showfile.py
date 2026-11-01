"""Say which file was picked.

The file picker took the file and said nothing: the form looked empty and
the user could not tell whether the button had done anything.  So the name
and the size of the picked file are shown where the path field is, and
the path field is marked as the other way in, not the only way.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

if "gFileName" not in s:
    # where the name goes, under the picker
    old = '选择本地文件</button>'
    new = ('选择本地文件</button>'
           '<span id="gFileName" class="muted" style="margin-left:8px;font-size:11.5px"></span>')
    assert old in s, "按钮锚点没找到"
    s = s.replace(old, new, 1)

    # and the handler that fills it
    js = '''
<script>
// say which file was picked: the name, and how big it is
(function(){
  const pick=document.getElementById("gFilePicker");
  const label=document.getElementById("gFileName");
  const path=document.getElementById("gSource");
  if(!pick||!label) return;
  pick.addEventListener("change",function(){
    const f=this.files&&this.files[0];
    if(!f){ label.textContent=""; return; }
    const kb=f.size/1024, sz=kb>1024?(kb/1024).toFixed(1)+" MB":Math.round(kb)+" KB";
    label.textContent="✓ 已选 "+f.name+"（"+sz+"）";
    if(path){ path.placeholder="（已选本地文件，路径可以留空）"; path.style.opacity=".55"; }
  });
})();
</script>
'''
    i = s.find("</body>")
    assert i > 0, "没找到 </body>"
    s = s[:i] + js + "\n" + s[i:]

p.write_text(s, encoding="utf-8")
print("index.html: 选中文件后显示文件名和大小")
