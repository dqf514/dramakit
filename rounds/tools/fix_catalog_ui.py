"""The catalog is read with a POST, the same as it is asked for."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

old = '  const r = await getJSON("/api/catalog?project="+encodeURIComponent(slug));'
new = '  const r = await postJSON("/api/catalog",{project:slug});'
if old in s:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("index.html: catalog 改成 POST")
else:
    # the file has it in another form; show what is there
    i = s.find("api/catalog")
    print("index.html: 锚点没找到，现在是：", repr(s[max(0, i-120):i+80]))
