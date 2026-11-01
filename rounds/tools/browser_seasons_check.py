"""Open the console and look at the workbench in a real browser.

The seasons panel was stitched into a page that is mostly template
literals, and a broken one does not fail loudly - the whole workbench
just goes blank. So this loads the page, picks the project, and reports
what the browser actually rendered, including any script errors.
"""
import json
from playwright.sync_api import sync_playwright

OUT = r"C:\Users\David\AppData\Local\Temp\opencode\seasons_panel.png"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append("console." + m.type + ": " + m.text)
            if m.type == "error" else None)

    page.goto("http://127.0.0.1:8080/", wait_until="networkidle")
    page.wait_for_selector("#projlist .proj", timeout=8000)
    page.query_selector("#projlist .proj").click()
    page.wait_for_timeout(1500)
    page.click('.railbtn[data-page="workbench"]')
    page.wait_for_timeout(2000)

    state = page.evaluate("""() => {
      const panel = document.getElementById("work-seasons");
      const list  = document.getElementById("seasonList");
      const hint  = document.getElementById("seasonHint");
      const btn   = document.querySelector('#page-workbench [onclick*="startSeason"]');
      const wb    = document.getElementById("page-workbench");
      return {
        panelVisible: !!panel && panel.style.display !== "none",
        listText: list ? list.innerText.slice(0, 90) : null,
        hint: hint ? hint.textContent : null,
        button: btn ? btn.textContent.trim() : null,
        episodesDrawn: wb ? wb.querySelectorAll(".epcard").length : 0,
        chaptersDrawn: document.querySelectorAll("#chapterList input").length,
      };
    }""")
    page.screenshot(path=OUT)

    print(json.dumps(state, ensure_ascii=False, indent=2))
    print()
    print("script errors:", errors[:6] if errors else "none")
    print("screenshot:", OUT)
    b.close()
