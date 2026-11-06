"""The three cards are the same height, and the chapter list scrolls.

Both views: the tiles and the list.  The card takes the height of the
row and the list takes what is left of it.

    python rounds/tools/shot_heights.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\heights.png")

MEASURE = """() => {
  const cards=[...document.querySelectorAll('.wb-setup > .card')];
  const body=document.querySelector('.chap-body');
  return {
    cards: cards.map(c=>({id:c.id||c.className, h:Math.round(c.getBoundingClientRect().height)})),
    bodyH: body?Math.round(body.getBoundingClientRect().height):0,
    bodyContent: body?Math.round(body.scrollHeight):0,
    scroll: body?body.scrollHeight>body.clientHeight:false,
    pageH: document.body.scrollHeight, viewH: window.innerHeight};
}"""


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
        page.wait_for_selector("#lookCard", timeout=20000)
        page.wait_for_timeout(4000)

        for mode, label in (("icon", "图标视图"), ("list", "列表视图")):
            if mode == "list":
                page.click("#chapMode")
                page.wait_for_timeout(800)
            m = page.evaluate(MEASURE)
            hs = [c["h"] for c in m["cards"]]
            print("  %s：" % label)
            for c in m["cards"]:
                print("     %-14s 高 %s" % (c["id"][:14], c["h"]))
            print("     三卡等高=%s  章节区 %s（内容 %s，滚动=%s）"
                  % (len(set(hs)) == 1, m["bodyH"], m["bodyContent"], m["scroll"]))
        page.screenshot(path=str(OUT))
        print("  截图:", OUT)
        print("  页面报错:", "; ".join(errors[:3]) if errors else "无")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
