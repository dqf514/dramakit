"""Does the running stage look alive, and can a reference be seen whole?

The panel claimed to be running while looking identical to a hung page,
and a reference sheet was a thumbnail too small to check a face. This
drives both: it reads the computed animation off the running panel, then
opens the cast page, clicks a picture, and pages through the character's
references with the keyboard.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
SHOT1 = r"C:\Users\David\AppData\Local\Temp\opencode\anim_panel.png"
SHOT2 = r"C:\Users\David\AppData\Local\Temp\opencode\lightbox.png"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(BASE, wait_until="networkidle")
    page.wait_for_selector("#projlist .proj", timeout=10000)
    page.query_selector("#projlist .proj").click()
    page.wait_for_timeout(2500)

    # ---- the running panel ------------------------------------------
    page.click('.railbtn[data-page="workbench"]')
    page.wait_for_timeout(2000)
    anim = page.evaluate("""() => {
      const pulse=document.querySelector("#progressSlot .pulse");
      const bar=document.querySelector("#progressSlot .prog-bar");
      const indet=document.querySelector("#progressSlot .prog-bar.indet");
      const fill=bar?bar.querySelector("i"):null;
      return {
        hasPulse: !!pulse,
        pulseAnimation: pulse?getComputedStyle(pulse).animationName:null,
        hasBar: !!bar,
        indeterminate: !!indet,
        barAnimation: indet?getComputedStyle(indet.querySelector("i")).animationName:null,
        determinateWidth: (!indet&&fill)?fill.style.width:null,
        stage: (document.querySelector("#progressSlot b")||{}).textContent||null,
      };
    }""")
    page.screenshot(path=SHOT1)

    # ---- the cast page and its viewer -------------------------------
    page.click('.railbtn[data-page="cast"]')
    page.wait_for_timeout(2500)
    pictures = page.evaluate("() => document.querySelectorAll('#page-cast .castcard img[data-i]').length")
    names = page.evaluate("""() => [].slice.call(document.querySelectorAll('#page-cast .castcard'))
                                .map(c=>c.dataset.name)""")

    lightbox = {"opened": False}
    if pictures:
        page.click("#page-cast .castcard img[data-i]")
        page.wait_for_timeout(1200)
        lightbox["opened"] = page.evaluate("() => !!document.querySelector('.lb-scrim')")
        first = page.evaluate("""() => ({
          src: (document.querySelector('.lb-body img')||{}).src||null,
          count: (document.querySelector('.lb-head .n')||{}).textContent||null,
          label: (document.querySelector('.lb-head .t')||{}).textContent||null,
          nextEnabled: !document.querySelector('.lb-foot .btn:last-child').disabled,
        })""")
        lightbox["first"] = first
        page.screenshot(path=SHOT2)

        # page with the keyboard, not the buttons
        if first.get("nextEnabled"):
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(700)
            lightbox["afterRight"] = page.evaluate("""() => ({
              count: (document.querySelector('.lb-head .n')||{}).textContent||null,
              src: (document.querySelector('.lb-body img')||{}).src||null,
            })""")
            page.keyboard.press("ArrowLeft")
            page.wait_for_timeout(700)
            lightbox["afterLeft"] = page.evaluate(
                "() => (document.querySelector('.lb-head .n')||{}).textContent||null")
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        lightbox["closedByEsc"] = page.evaluate("() => !document.querySelector('.lb-scrim')")

    print("=== 进度面板动画 ===")
    print(json.dumps(anim, ensure_ascii=False, indent=2))
    print()
    print("=== 角色照片查看器 ===")
    print("角色:", names)
    print("可点图片数:", pictures)
    print(json.dumps(lightbox, ensure_ascii=False, indent=2))
    print()
    print("页面错误:", errors[:5] if errors else "无")
    b.close()
