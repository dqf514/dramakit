"""Does the workbench say what the后台 is doing?

The panel was the whole point: a task was submitted and the page was
silent. This opens the console on the running project and reads what the
browser actually renders - the stage, the elapsed time, the strip - and
watches a second reading to prove the poll moves on its own.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
SHOT = r"C:\Users\David\AppData\Local\Temp\opencode\progress_panel.png"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(BASE, wait_until="networkidle")
    page.wait_for_selector("#projlist .proj", timeout=10000)
    # the project that is running is the one with a running stage
    slugs = page.evaluate("() => (S.projects||[]).map(p=>p.slug)")
    page.query_selector("#projlist .proj").click()
    page.wait_for_timeout(2500)
    page.click('.railbtn[data-page="workbench"]')
    page.wait_for_timeout(2000)

    def read():
        return page.evaluate("""() => {
          const slot=document.getElementById("progressSlot");
          const panel=slot?slot.firstElementChild:null;
          const spin=document.querySelector("#progressSlot .spin");
          const strip=[].slice.call(document.querySelectorAll("#progressSlot .prog-strip span"));
          return {
            hasSlot: !!slot,
            panelVisible: !!panel,
            spinning: !!spin,
            stage: panel? (panel.querySelector("b")||{}).textContent : null,
            running: panel? (panel.innerText.match(/已运行[^\\n]*/)||[""])[0] : null,
            hint: panel? ((panel.querySelectorAll("div")[0]||{}).textContent||"").slice(0,40) : null,
            stripDone: strip.filter(x=>x.style.color.indexOf("34")>=0||x.textContent.indexOf("●")===0).length,
            stripRunning: strip.filter(x=>x.textContent.indexOf("◐")===0).length,
            stripTotal: strip.length,
          };
        }""")

    first = read()
    page.screenshot(path=SHOT)
    # wait and read again: the poll must advance the clock by itself
    page.wait_for_timeout(9000)
    second = read()

    print("=== 工作台进度面板（浏览器实测）===")
    print(json.dumps({"项目": slugs, "第一次": first, "9 秒后": second},
                     ensure_ascii=False, indent=2))
    print()
    print("页面错误:", errors[:5] if errors else "无")
    print("截图:", SHOT)
    b.close()
