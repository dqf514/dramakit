"""A look at the workbench after the changes.

The cover is as tall as the text beside it, the steps are in the row
with the book, the buttons that repeated the tabs are gone, and the
chapters start with none of them picked.

    python rounds/tools/shot_head.py
"""
from __future__ import annotations

import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\head.png")


def main() -> int:
    with urllib.request.urlopen(BASE + "/api/projects", timeout=20) as r:
        import json
        ps = json.loads(r.read()).get("projects") or []
    if not ps:
        print("  没有项目")
        return 1
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
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT))
        print("  截图:", OUT)

        info = page.evaluate("""() => {
          const head=document.querySelector('.wb-head');
          const hero=document.querySelector('.hero');
          const cover=document.querySelector('.hero .cover');
          const hb=document.querySelector('.hero .hb');
          const steps=document.querySelector('.wb-head .card');
          const tiles=[...document.querySelectorAll('#chapterList .chap-tile')];
          const on=tiles.filter(t=>t.classList.contains('on')).length;
          return {
            cols:getComputedStyle(head).gridTemplateColumns,
            coverH:Math.round(cover.getBoundingClientRect().height),
            coverW:Math.round(cover.getBoundingClientRect().width),
            textH:Math.round(hb.getBoundingClientRect().height),
            heroH:Math.round(hero.getBoundingClientRect().height),
            stepsW:Math.round(steps.getBoundingClientRect().width),
            stepH:Math.round(document.querySelector('.step').getBoundingClientRect().height),
            tiles:tiles.length, on:on,
            oldButtons:document.querySelectorAll('#page-flow [data-act]').length,
            pageH:document.body.scrollHeight, viewH:window.innerHeight};
        }""")
        print("  两列:", info["cols"])
        print("  封面 %sx%s  文字高 %s  （等高=%s）"
              % (info["coverW"], info["coverH"], info["textH"],
                 abs(info["coverH"] - info["textH"]) <= 2))
        print("  步骤卡宽 %s，单步高 %s" % (info["stepsW"], info["stepH"]))
        print("  章节 %d 个，选中 %d 个（应为 0）" % (info["tiles"], info["on"]))
        print("  旧按钮还剩 %d 个（应为 0）" % info["oldButtons"])
        print("  页面高 %d / 视口 %d" % (info["pageH"], info["viewH"]))
        print("  页面报错:", "; ".join(errors[:3]) if errors else "无")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
