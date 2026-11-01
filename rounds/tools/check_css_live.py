"""Did the progress panel's CSS actually reach the page?

The rules were inserted with their own <style> tag inside the block that
was already open, and <style> is a raw-text element: everything after the
inner tag is literal text until the first </style>, so a spinner can look
right in a screenshot while its animation never ran. This asks the browser
what it computed rather than what the file says.
"""
import json
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 950})
    page.goto("http://127.0.0.1:8080/", wait_until="networkidle")
    page.wait_for_selector("#projlist .proj", timeout=10000)
    page.query_selector("#projlist .proj").click()
    page.wait_for_timeout(2500)
    page.click('.railbtn[data-page="workbench"]')
    page.wait_for_timeout(2000)

    out = page.evaluate("""() => {
      const spin=document.querySelector("#progressSlot .spin");
      const strip=document.querySelector("#progressSlot .prog-strip");
      const cs=spin?getComputedStyle(spin):null;
      const ss=strip?getComputedStyle(strip):null;
      return {
        styleTags: document.querySelectorAll("style").length,
        hasSpin: !!spin,
        spinAnimation: cs?cs.animationName:null,
        spinDuration: cs?cs.animationDuration:null,
        stripFontSize: ss?ss.fontSize:null,
        // does the stylesheet hold the keyframes at all?
        keyframesFound: (function(){
          for(const sh of document.styleSheets){
            try{ for(const r of sh.cssRules){ if(r.type===7||/dkspin/.test(r.cssText||"")) return true; } }catch(e){}
          }
          return false;
        })(),
      };
    }""")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    b.close()
