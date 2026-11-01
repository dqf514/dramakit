"""A scene's reference can be seen whole too, and one style stays ours.

The viewer opened a character's pictures; a scene's reference was still a
thumbnail in the corner of the cast page, and a place is checked the same
way a face is - by looking at it. Scene pictures now open in the same
viewer, one list per scene, paged the same way.

The progress panel also brought a .spin rule that matched a spinner the
page already had, and being later in the sheet it restyled that one too.
The rule is scoped to the panel now: what the panel added, the panel owns.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

if "__locImgs" in s:
    print("index.html: 场景图已接入查看器，跳过")
    raise SystemExit(0)

# ---------------------------------- 1. scope the panel's spinner to itself
old_spin = """.spin{display:inline-block;width:11px;height:11px;border:2px solid var(--line);
  border-top-color:var(--confirm);border-radius:50%;
  animation:dkspin .9s linear infinite;vertical-align:-1px}"""
new_spin = """#progressSlot .spin{display:inline-block;width:11px;height:11px;
  border:2px solid var(--line);border-top-color:var(--confirm);border-radius:50%;
  animation:dkspin .9s linear infinite;vertical-align:-1px}"""
assert old_spin in s, ".spin 规则锚点没找到"
s = s.replace(old_spin, new_spin, 1)

# ---------------------------------- 2. the scene pictures join the viewer --
old_loc = '''  const locs=(d.locations||[]).map(l=>`<div class="loc"><b>${esc(l.name)}</b>
    <div class="muted" style="font-size:10.5px;margin-top:2px">${esc((l.description||"").slice(0,44))}</div>
    <div class="li">${(l.ref_urls||[]).map(u=>`<img src="${u}" loading="lazy">`).join("")||'<span class="muted" style="font-size:10px">无参考图</span>'}</div>
  </div>`).join("");'''
new_loc = '''  // a scene is checked by looking at it, so its pictures go in the same
  // list the viewer walks as the characters'
  window.__locImgs={};
  const locs=(d.locations||[]).map(l=>{
    const imgs=(l.ref_urls||[]).filter(Boolean);
    window.__locImgs[l.name]=imgs;
    return `<div class="loc" data-loc="${attr(l.name)}"><b>${esc(l.name)}</b>
    <div class="muted" style="font-size:10.5px;margin-top:2px">${esc((l.description||"").slice(0,44))}</div>
    <div class="li">${imgs.map((u,k)=>`<img src="${u}" loading="lazy" data-i="${k}">`).join("")||'<span class="muted" style="font-size:10px">无参考图</span>'}</div>
  </div>`;}).join("");'''
assert old_loc in s, "场景渲染锚点没找到"
s = s.replace(old_loc, new_loc, 1)

# ---------------------------------- 3. and the handler, same delegation ---
old_wire = '''function wireCastViewer(){
  // delegated, so a re-render does not need rewiring each picture
  $$("#page-cast .castcard img[data-i]").forEach(img=>{
    img.style.cursor="zoom-in";
    img.onclick=()=>{
      const card=img.closest(".castcard");
      const name=card?card.dataset.name:"";
      const list=(window.__castImgs||{})[name]||[];
      openLightbox(list, Number(img.dataset.i)||0, name||"参考图");
    };
  });
}'''
new_wire = '''function wireCastViewer(){
  // delegated, so a re-render does not need rewiring each picture
  $$("#page-cast .castcard img[data-i]").forEach(img=>{
    img.style.cursor="zoom-in";
    img.onclick=()=>{
      const card=img.closest(".castcard");
      const name=card?card.dataset.name:"";
      const list=(window.__castImgs||{})[name]||[];
      openLightbox(list, Number(img.dataset.i)||0, name||"参考图");
    };
  });
  // scenes the same way: a place is checked by looking at it
  $$("#page-cast .loc img[data-i]").forEach(img=>{
    img.style.cursor="zoom-in";
    img.onclick=()=>{
      const box=img.closest(".loc");
      const name=box?box.dataset.loc:"";
      const list=(window.__locImgs||{})[name]||[];
      openLightbox(list, Number(img.dataset.i)||0, "场景 · "+(name||"参考图"));
    };
  });
}'''
assert old_wire in s, "wireCastViewer 锚点没找到"
s = s.replace(old_wire, new_wire, 1)

p.write_text(s, encoding="utf-8")
print("index.html: 场景参考图也能点开放大翻页了")
print("  · 场景和角色用同一个查看器，← → 翻页、Esc 关闭")
print("  · 面板的转圈样式限定在面板内，不再覆盖页面原有的 .spin")
