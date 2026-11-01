"""Ask the live page why .wb-layout is not a grid."""
import json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#projlist .proj", timeout=8000)
    pg.query_selector("#projlist .proj").click()
    pg.wait_for_timeout(2000)
    pg.click('.railbtn[data-page="workbench"]')
    pg.wait_for_timeout(1500)

    out = pg.evaluate("""() => {
      const L = document.querySelector('.wb-layout');
      const res = { found: !!L };
      if (!L) return res;
      // does the class actually match the element?
      res.className = L.className;
      res.tagName = L.tagName;
      // walk every stylesheet rule that mentions wb-layout
      const rules = [];
      for (const sheet of document.styleSheets) {
        let list; try { list = sheet.cssRules; } catch(e){ continue; }
        for (const r of list) {
          if (r.cssText && r.cssText.includes('wb-layout')) rules.push(r.cssText);
        }
      }
      res.matchingRules = rules;
      // the element's real tag + first 200 chars of outerHTML
      res.outer = L.outerHTML.slice(0, 200);
      return res;
    }""")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    b.close()
