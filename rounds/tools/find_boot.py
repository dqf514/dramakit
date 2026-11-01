"""Find the page's boot code: what runs when it first loads."""
from pathlib import Path

s = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html").read_text(
    encoding="utf-8", errors="replace")

for key in ("async function loadProjects", "loadProjects()", 'switchPage("guide")',
            "window.addEventListener", "window.onload", "setInterval"):
    i = s.find(key)
    if i > 0:
        print(f"=== {key}  位置 {i} ===")
        print(s[i:i + 420].replace("\n", " | ")[:420])
        print()
