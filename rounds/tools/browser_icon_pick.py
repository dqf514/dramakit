"""Pick in icon mode, press start, watch the job.

The button used to throw on line one.  And in icon mode picking did
nothing, because the chosen set was only read from checkboxes that do not
exist there.  Both are checked here: a tile pick moves the count, and the
button saves the pick and starts the job.
"""
import json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#projlist .proj", timeout=8000)
    pg.query_selector("#projlist .proj").click()
    pg.wait_for_timeout(2200)
    pg.click('.railbtn[data-page="workbench"]')
    pg.wait_for_timeout(1600)

    # switch to icon mode and pick one tile
    pg.evaluate("() => toggleChapMode()")
    pg.wait_for_timeout(500)
    tiles = pg.evaluate("() => document.querySelectorAll('#chapterList .chap-tile').length")
    pg.evaluate("() => setAllChapters(false)")
    pg.wait_for_timeout(300)
    none = pg.evaluate("() => document.getElementById('chapterHint').textContent")
    pg.evaluate("() => { const t=document.querySelectorAll('#chapterList .chap-tile')[0]; _chapTile(t); }")
    pg.wait_for_timeout(300)
    one = pg.evaluate("() => document.getElementById('chapterHint').textContent")
    # press start, capture toasts
    pg.evaluate("""() => { window.__cap=[]; const o=toast;
        toast=(m,k,ms)=>{ window.__cap.push(String(m)); o(m,k,ms); }; }""")
    pg.click('#work-chapters .btn.go')
    pg.wait_for_timeout(5000)
    captured = pg.evaluate("() => window.__cap")

    # what did the server record?
    saved = pg.evaluate("""async () => {
      const slug = S.current;
      const r = await fetch('/api/catalog', {method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({project: slug})}).then(x=>x.json());
      return {chosen: r.chosen, seg_wanted: r.episodes_wanted};
    }""")

    print("=== 图标模式点选 + 开始制作 ===")
    print("  图标块数:", tiles)
    print("  全不选后:", none)
    print("  点1个后:", one)
    print("  toast:", json.dumps(captured, ensure_ascii=False))
    print("  服务器记录:", json.dumps(saved, ensure_ascii=False))
    print("  页面错误:", errs or "（无）")
    pg.screenshot(path=r"C:\Users\David\AppData\Local\Temp\opencode\icon_pick.png")
    b.close()
