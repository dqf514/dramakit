"""Measure the real geometry of the workbench columns."""
import json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#projlist .proj", timeout=8000)
    pg.query_selector("#projlist .proj").click()
    pg.wait_for_timeout(2500)
    pg.click('.railbtn[data-page="workbench"]')
    pg.wait_for_timeout(1800)

    g = pg.evaluate("""() => {
      const L=document.querySelector('.wb-layout'), M=document.querySelector('.wb-main'),
            R=document.querySelector('.wb-rail'), C=document.getElementById('work-chapters');
      const box=(e)=>e?{x:Math.round(e.getBoundingClientRect().x),y:Math.round(e.getBoundingClientRect().y),w:Math.round(e.getBoundingClientRect().width)}:null;
      const cs=L?getComputedStyle(L):null;
      return {layout:box(L), main:box(M), rail:box(R), card:box(C),
              display:cs&&cs.display, cols:cs&&cs.gridTemplateColumns};
    }""")
    print(json.dumps(g, ensure_ascii=False, indent=2))
    b.close()
