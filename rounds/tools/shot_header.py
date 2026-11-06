"""The header, the rail, and the narrow layout.

    python rounds/tools/shot_header.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\header.png")


def look(page):
    return page.evaluate("""() => {
      const h=document.querySelector('header');
      const rail=document.getElementById('rail');
      const side=document.getElementById('side');
      const main=document.getElementById('main');
      const vis=(e)=>{ if(!e) return false; const r=e.getBoundingClientRect();
                       return r.width>0 && r.height>0 && getComputedStyle(e).display!=='none'; };
      return {
        header:[...h.querySelectorAll('button')].map(b=>b.id||b.title),
        rail:[...rail.querySelectorAll('button')].filter(vis).map(b=>b.dataset.page||b.id),
        sideShown: vis(side),
        sideTop: Math.round(side.getBoundingClientRect().top),
        mainTop: Math.round(main.getBoundingClientRect().top),
        proj: document.querySelectorAll('#projlist .proj').length};
    }""")


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
        page.wait_for_timeout(3000)

        for w, h, label in ((2560, 1400, "宽 2560"), (1100, 1200, "中 1100"), (640, 1000, "手机 640")):
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(2000)
            info = look(page)
            print("  %s:" % label)
            print("     页首按钮:", info["header"])
            print("     左栏可见:", info["rail"])
            print("     项目栏 显示=%s 顶%s；工作区顶%s；项目 %s 个"
                  % (info["sideShown"], info["sideTop"], info["mainTop"], info["proj"]))
        page.set_viewport_size({"width": 2560, "height": 1400})
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT))
        print("  截图:", OUT)
        print("  页面报错:", "; ".join(errors[:3]) if errors else "无")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
