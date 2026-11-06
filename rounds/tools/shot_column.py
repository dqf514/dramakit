"""The column of projects: the list, the tags, the form, the panel.

    python rounds/tools/shot_column.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\column.png")


def main() -> int:
    with urllib.request.urlopen(BASE + "/api/projects", timeout=20) as r:
        ps = json.loads(r.read()).get("projects") or []
    slug = ps[0]["slug"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 2560, "height": 1400})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_selector("#projlist .proj", timeout=20000)
        page.click(f'#projlist .proj[data-slug="{slug}"]')
        page.wait_for_selector("#flowNewFold", timeout=20000)
        page.wait_for_timeout(3500)
        # open both panels in the column
        page.evaluate("""() => {
          document.getElementById('flowNewFold')?.setAttribute('open','');
          document.getElementById('projectManagement')?.setAttribute('open','');
        }""")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT))
        print("  截图:", OUT)

        info = page.evaluate("""() => {
          const side=document.getElementById('side');
          const kids=[...side.querySelectorAll('.side-content > *')].map(e=>{
            const r=e.getBoundingClientRect();
            return {id:e.id||e.className, top:Math.round(r.top), h:Math.round(r.height)};
          });
          const form=document.getElementById('flowNewBody');
          const fields=[...form.querySelectorAll('input.f, button')].map(e=>{
            const r=e.getBoundingClientRect();
            return {id:e.id, x:Math.round(r.left), y:Math.round(r.top), w:Math.round(r.width)};
          });
          const pm=document.getElementById('projectManagement');
          const pageForm=document.getElementById('page-flow')?.querySelector('#flowNewFold');
          return {kids, fields, sideH:Math.round(side.getBoundingClientRect().height),
                  pmBottom: pm?Math.round(pm.getBoundingClientRect().bottom):null,
                  pageHasForm: !!pageForm};
        }""")
        print("  侧栏从上到下:")
        for k in info["kids"]:
            print("     %-16s 顶 %-5s 高 %s" % (k["id"][:16], k["top"], k["h"]))
        print("  表单里的字段（竖着 = y 各不相同）:")
        for f in info["fields"]:
            print("     %-14s x=%-5s y=%-5s 宽 %s" % (f["id"], f["x"], f["y"], f["w"]))
        print("  管理面板底边 %s / 侧栏高 %s（贴底=%s）"
              % (info["pmBottom"], info["sideH"], info["pmBottom"] == info["sideH"]))
        print("  工作台页面里还有没有新建表单:", info["pageHasForm"])
        print("  页面报错:", "; ".join(errors[:3]) if errors else "无")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
