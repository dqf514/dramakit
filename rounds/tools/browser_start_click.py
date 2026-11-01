"""Click the start button and watch what happens.

Before the fix it threw "incompatible receiver" on line one and nothing
happened.  Now it should save the pick, start the job, and follow it.
"""
import json, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs, toasts = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: toasts.append(m.text) if m.type == "error" else None)

    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#projlist .proj", timeout=8000)
    pg.query_selector("#projlist .proj").click()
    pg.wait_for_timeout(2200)
    pg.click('.railbtn[data-page="workbench"]')
    pg.wait_for_timeout(1600)

    # pick exactly one chapter, then press start
    pg.evaluate("() => setAllChapters(false)")
    pg.wait_for_timeout(300)
    before = pg.evaluate("() => document.getElementById('chapterHint').textContent")
    pg.evaluate("() => { const t=document.querySelectorAll('#chapterList .chap-tile')[0]; if(t) _chapTile(t); }")
    pg.wait_for_timeout(300)
    one = pg.evaluate("() => document.getElementById('chapterHint').textContent")

    # press the button, capture the toast and any job id
    pg.evaluate("""() => { window.__cap = []; const o = toast;
        toast = (m,k,ms) => { window.__cap.push(String(m)); o(m,k,ms); }; }""")
    pg.click('#work-chapters .btn.go')
    pg.wait_for_timeout(4000)
    captured = pg.evaluate("() => window.__cap")

    # is a job running?
    job = pg.evaluate("""async () => {
      const r = await fetch('/api/jobs').then(x=>x.json()).catch(()=>null);
      return r;
    }""")

    print("=== 点击「开始制作」实测 ===")
    print("  点选前:", before)
    print("  选中1章:", one)
    print("  toast:", json.dumps(captured, ensure_ascii=False))
    print("  页面错误:", errs or "（无）")
    print("  控制台 error:", toasts or "（无）")
    print("\n截图已存。")
    pg.screenshot(path=r"C:\Users\David\AppData\Local\Temp\opencode\start_click.png")
    b.close()
