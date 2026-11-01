"""Remember where the user was, so a refresh does not throw them out.

This is a single-page app, so the browser's refresh button restarted the
script: S.booted was undefined again, and the page fell back to the guide
- losing the project and the screen the user was on.  The page now keeps
its place in the URL (#project/page) and reads it back on load, so
refreshing lands where you were, and the address can be shared or
bookmarked.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

# 1. leaving a page writes where we are
old = """  if(name==="guide") renderGuide();"""
new = """  // remember where we are: a refresh should come back to it
  try{ if(S.current) location.replace("#"+S.current+"/"+name); }catch(e){}
  if(name==="guide") renderGuide();"""
if old in s:
    s = s.replace(old, new, 1)
    print("index.html: 切页时写入 URL")

# 2. coming back reads it
old2 = """  if(!S.booted){ S.activePage = S.projects.length ? "workbench" : "guide"; S.booted=true; }"""
new2 = """  if(!S.booted){
    // a refresh lands where the user was: #project/page in the address
    let pg="", pj="";
    try{
      const m=(location.hash||"").replace(/^#/,"").split("/");
      if(m.length>=2){ pj=decodeURIComponent(m[0]||""); pg=m[1]||""; }
    }catch(e){}
    if(pj && S.projects.some(x=>x.slug===pj) && pj!==S.current){
      S.current=pj; await selectProject(pj, true);
    }
    const known=["guide","workbench","board","cast","pipeline","assets","settings"];
    S.activePage = pg && known.includes(pg) ? pg
                 : (S.projects.length ? "workbench" : "guide");
    S.booted=true;
  }"""
if old2 in s:
    s = s.replace(old2, new2, 1)
    print("index.html: 刷新时读回 URL 位置")

p.write_text(s, encoding="utf-8")
print("index.html: 刷新不再回到引导页")
