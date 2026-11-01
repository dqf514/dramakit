"""Open the chapter reader in a real browser and check it works."""
import json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
SHOT = r"C:\Users\David\AppData\Local\Temp\opencode\reader.png"

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
    pg.wait_for_timeout(1800)

    # open the reader from a list row's chapter title
    pg.click(".rd-open >> nth=0")
    pg.wait_for_timeout(1200)

    def state():
        return pg.evaluate("""() => {
          const t=document.getElementById('rdTitle'), v=document.getElementById('rdVol'),
                body=document.getElementById('rdBody'), pos=document.getElementById('rdPos'),
                prev=document.getElementById('rdPrev'), next=document.getElementById('rdNext');
          return { title:t?t.textContent:null, vol:v?v.textContent:null,
                   bodyLen:body?body.textContent.length:0,
                   bodyHead:body?body.textContent.slice(0,60):null,
                   pos:pos?pos.textContent:null,
                   prevDisabled:prev?prev.disabled:null,
                   nextDisabled:next?next.disabled:null };
        }""")

    s1 = state()
    pg.screenshot(path=SHOT)

    # page forward and back
    pg.click("#rdNext"); pg.wait_for_timeout(1000); s2 = state()
    pg.click("#rdPrev"); pg.wait_for_timeout(1000); s3 = state()

    # arrow key + escape
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(800); s4 = state()
    pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
    closed = pg.evaluate("() => !document.querySelector('.rd-scrim')")

    print("=== 章节阅读器（浏览器实测）===")
    print(json.dumps({
        "打开第1章": s1,
        "点下一章": s2["title"],
        "点上一章": s3["title"],
        "按→键": s4["title"],
        "Esc已关闭": closed,
        "页面错误": errs[:5] or "（无）",
    }, ensure_ascii=False, indent=2))
    print("\n截图:", SHOT)
    b.close()
