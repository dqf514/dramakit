import pathlib

p = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html")
b = p.read_bytes()
print("  CRLF 数量:", b.count(b"\r\n"), "| 单独 LF:", b.count(b"\n") - b.count(b"\r\n"))
t = p.read_text(encoding="utf-8")
i = t.find('data-chap="season"')
print(repr(t[i - 300:i + 200]))
