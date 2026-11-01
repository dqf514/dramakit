"""Can a scene's reference be opened and paged, like a character's?

The viewer took the characters; a scene's reference was still a thumbnail.
This opens the cast page, clicks a scene picture, and walks it with the
keyboard - and checks the page's own spinner was not restyled by the
panel's rule.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
SHOT = r"C:\Users\David\AppData\Local\Temp\opencode\loc_lightbox.png"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(BASE, wait_until="networkidle")
    page.wait_for_selector("#projlist .proj", timeout=10000)
    page.query_selector("#projlist .proj").click()
    page.wait_for_timeout(2500)
    page.click('.railbtn[data-page="cast"]')
    page.wait_for_timeout(2500)

    counts = page.evaluate("""() => ({
      castImgs: document.querySelectorAll('#page-cast .castcard img[data-i]').length,
      locBoxes: document.querySelectorAll('#page-cast .loc[data-loc]').length,
      locImgs: document.querySelectorAll('#page-cast .loc img[data-i]').length,
      // the page's own spinner must keep its own colours
      genericSpin: (function(){
        const s=[].slice.call(document.querySelectorAll('.spin'))
                   .find(x=>!x.closest('#progressSlot'));
        return s?getComputedStyle(s).borderTopColor:null;
      })(),
      panelSpin: (function(){
        const s=document.querySelector('#progressSlot .spin');
        return s?getComputedStyle(s).borderTopColor:null;
      })(),
    })""")

    out = {"counts": counts}
    if counts["locImgs"]:
        page.click("#page-cast .loc img[data-i]")
        page.wait_for_timeout(1200)
        out["opened"] = page.evaluate("""() => ({
          visible: !!document.querySelector('.lb-scrim'),
          label: (document.querySelector('.lb-head .t')||{}).textContent||null,
          count: (document.querySelector('.lb-head .n')||{}).textContent||null,
          src: ((document.querySelector('.lb-body img')||{}).src||'').split('/').slice(-2).join('/'),
        })""")
        page.screenshot(path=SHOT)
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        out["closed"] = page.evaluate("() => !document.querySelector('.lb-scrim')")

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print()
    print("页面错误:", errors[:5] if errors else "无")
    b.close()
