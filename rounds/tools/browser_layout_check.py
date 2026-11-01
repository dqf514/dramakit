"""Drive the reworked workbench in a real browser: layout, icon mode, select-all.

Checks the things a screenshot alone would not: that the chapter rail sits
in its own column to the right, that icon mode renders a tile grid, that
select-all/none move the counter, and that picks survive a mode switch.
"""
import json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
SHOT = r"C:\Users\David\AppData\Local\Temp\opencode\wb_layout.png"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#projlist .proj", timeout=8000)
    pg.query_selector("#projlist .proj").click()
    pg.wait_for_timeout(2500)
    pg.click('.railbtn[data-page="workbench"]')
    pg.wait_for_timeout(2000)

    def probe():
        return pg.evaluate("""() => {
          const rail=document.querySelector('.wb-rail');
          const main=document.querySelector('.wb-main');
          const card=document.getElementById('work-chapters');
          const hint=document.getElementById('chapterHint');
          const tiles=document.querySelectorAll('.chap-tile');
          const boxes=document.querySelectorAll('#chapterList input[type=checkbox]');
          const onTiles=document.querySelectorAll('.chap-tile.on');
          return {
            twoCol: !!(rail&&main),
            railRight: rail&&main ? rail.getBoundingClientRect().left > main.getBoundingClientRect().right - 5 : false,
            cardVisible: card ? card.style.display!=='none' : false,
            tiles: tiles.length, onTiles: onTiles.length, boxes: boxes.length,
            hint: hint?hint.textContent:null,
          };
        }""")

    list_state = probe()

    # switch to icon mode
    pg.click("#chapMode")
    pg.wait_for_timeout(600)
    icon_state = probe()
    pg.screenshot(path=SHOT)

    # select none, then all
    pg.click("text=全不选"); pg.wait_for_timeout(400); none_state = probe()
    pg.click("text=全选");   pg.wait_for_timeout(400); all_state  = probe()

    # pick a single tile, confirm the counter ticks
    if icon_state["tiles"]:
        pg.click(".chap-tile >> nth=2"); pg.wait_for_timeout(300)
    single = probe()

    print("=== 工作台布局 & 章节交互（浏览器实测）===")
    print(json.dumps({
        "列表模式": list_state,
        "图标模式": icon_state,
        "点了全不选": none_state,
        "点了全选": all_state,
        "点开一个后的计数": single["hint"],
    }, ensure_ascii=False, indent=2))
    print("\n=== 页面错误 ===")
    print("\n".join("  " + e for e in errs[:8]) or "   （无）")
    print("\n截图:", SHOT)
    b.close()
