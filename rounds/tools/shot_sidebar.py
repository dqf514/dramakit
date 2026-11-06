"""The management panel is in the column of projects now.

    python rounds/tools/shot_sidebar.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\sidebar.png")


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
        # open the panel and look at it
        page.evaluate("document.getElementById('projectManagement')?.setAttribute('open','')")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT))
        print("  截图:", OUT)

        info = page.evaluate("""() => {
          const pm=document.getElementById('projectManagement');
          const side=document.getElementById('side');
          const r=pm?pm.getBoundingClientRect():null;
          const sr=side?side.getBoundingClientRect():null;
          return {
            inSide: !!(pm && side && side.contains(pm)),
            w: r?Math.round(r.width):0, sideW: sr?Math.round(sr.width):0,
            summary: pm?pm.querySelector('summary')?.textContent.trim():'',
            buttons: pm?[...pm.querySelectorAll('button')].map(b=>b.textContent.trim()):[],
            atBottom: pm?Math.round(r.bottom):0, viewH: window.innerHeight};
        }""")
        print("  在项目栏里:", info["inSide"])
        print("  宽度 %s / 侧栏 %s" % (info["w"], info["sideW"]))
        print("  标题:", info["summary"], " 按钮:", info["buttons"])
        print("  底边 %s / 视口 %s" % (info["atBottom"], info["viewH"]))
        print("  页面报错:", "; ".join(errors[:3]) if errors else "无")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
