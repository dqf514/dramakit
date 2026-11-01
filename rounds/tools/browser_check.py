"""Open the console in a real headless browser and report what renders.

Not a grep of the source: this loads the page, waits for the workbench to
draw, clicks into the project, and prints the browser's own console errors
plus whether the chapter list actually has rows in the DOM.
"""
import json
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page()
    errors, logs = [], []
    page.on("console", lambda m: (logs.append(f"[{m.type}] {m.text}"),
                                  errors.append(m.text) if m.type == "error" else None))
    page.on("pageerror", lambda e: errors.append(f"PAGEERROR: {e}"))

    page.goto(BASE, wait_until="networkidle")

    # click the first project in the sidebar, if any
    page.wait_for_selector("#projlist .proj", timeout=8000)
    first = page.query_selector("#projlist .proj")
    title = first.inner_text().split("\n")[0].strip() if first else "?"
    first.click()

    # let the workbench draw + chapters load
    page.wait_for_timeout(3000)

    # go to the workbench page explicitly
    page.click('.railbtn[data-page="workbench"]')
    page.wait_for_timeout(2500)

    info = page.evaluate("""() => {
      const card = document.getElementById("work-chapters");
      const list = document.getElementById("chapterList");
      const pageWb = document.getElementById("page-workbench");
      return {
        project: (window.S && S.current) || null,
        activePage: (window.S && S.activePage) || null,
        detailLoaded: !!(window.S && S.detail),
        cardExists: !!card,
        cardVisible: card ? (card.style.display !== "none" && card.offsetParent !== null) : false,
        listExists: !!list,
        listHTMLlen: list ? list.innerHTML.length : -1,
        listRows: list ? list.querySelectorAll("label").length : -1,
        workbenchVisible: pageWb ? pageWb.offsetParent !== null : false,
        workbenchStart: pageWb ? pageWb.innerText.slice(0, 120) : null,
      };
    }""")

    print("=== 点击的项目 ===")
    print(" ", title)
    print()
    print("=== 浏览器实测 DOM ===")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print()
    print("=== 控制台错误 ===")
    for e in errors[:12]:
        print("  ", e)
    if not errors:
        print("   （无）")
    print()
    print("=== 控制台日志（前 8 条）===")
    for l in logs[:8]:
        print("  ", l)

    page.screenshot(path=r"C:\Users\David\AppData\Local\Temp\opencode\workbench.png", full_page=False)
    print()
    print("截图: C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\workbench.png")

    browser.close()
