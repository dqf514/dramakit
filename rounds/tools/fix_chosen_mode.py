"""The chosen chapters had two sources of truth, and icon mode had neither.

_chapChosenSet rebuilt the set from checkboxes - which only exist in list
mode.  So in the icon grid, picking a tile or pressing 全选 / 全不选 moved
nothing: the set stayed stale and the count stayed where it was.

The set is now read from whichever mode is on screen - the checkboxes in
list mode, the tiles in icon mode - and the icon's tick follows the set,
so a pick looks the same in both views and means the same thing to the
button.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

old = """function _chapChosenSet(){
  // the set of picked chapter indices, rebuilt from the DOM if we have one
  const boxes=[].slice.call(document.querySelectorAll("#chapterList input[type=checkbox]"));
  if(boxes.length){
    window.__chosen=new Set(boxes.filter(b=>b.checked).map(b=>Number(b.dataset.idx)));
  }
  if(!window.__chosen) window.__chosen=new Set();
  return window.__chosen;
}"""

new = """function _chapChosenSet(){
  // The picked chapters, read from whichever mode is on screen.  List mode
  // shows checkboxes, icon mode shows tiles; taking only one of them left
  // the other view picking nothing at all.
  const boxes=[].slice.call(document.querySelectorAll("#chapterList input[type=checkbox]"));
  if(boxes.length){
    window.__chosen=new Set(boxes.filter(b=>b.checked).map(b=>Number(b.dataset.idx)));
  } else {
    const tiles=[].slice.call(document.querySelectorAll("#chapterList .chap-tile"));
    if(tiles.length){
      window.__chosen=new Set(tiles.filter(t=>t.classList.contains("on"))
                                   .map(t=>Number(t.dataset.idx)));
    }
  }
  if(!window.__chosen) window.__chosen=new Set();
  return window.__chosen;
}"""

assert old in s, "_chapChosenSet 锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("index.html: 选中状态在列表/图标两种模式下都读得到")
