"""The bar along the bottom, and the chapters that say where they are.

    python rounds/tools/shot_statusbar.py
"""
from __future__ import annotations

import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\statusbar.png")


def main() -> int:
    with urllib.request.urlopen(BASE + "/api/projects", timeout=20) as r:
        import json
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
        page.wait_for_timeout(6000)
        page.screenshot(path=str(OUT))
        print("  截图:", OUT)

        info = page.evaluate("""() => {
          const bar=document.getElementById('statusbar');
          const r=bar?bar.getBoundingClientRect():null;
          const tiles=[...document.querySelectorAll('#chapterList .chap-tile')];
          const by={};
          tiles.forEach(t=>{ const k=t.className.match(/st-\\w+/)?.[0]||'none';
                             by[k]=(by[k]||0)+1; });
          return {
            bar: !!bar,
            bottom: r?Math.round(r.bottom):null,
            viewH: window.innerHeight,
            fixed: bar?getComputedStyle(bar).position:null,
            chips: [...document.querySelectorAll('#statusbar .envchip')].map(c=>c.textContent),
            nodes: document.querySelector('#statusbar .sb-nodes')?.textContent||'',
            ticker: document.querySelector('#statusbar .sb-track span')?.textContent||'',
            by: by, tiles: tiles.length,
            envRowLeft: document.querySelectorAll('.envrow').length,
            pageH: document.body.scrollHeight};
        }""")
        print("  状态栏: %s  位置=%s  底边=%s / 视口 %s（贴底=%s）"
              % (info["bar"], info["fixed"], info["bottom"], info["viewH"],
                 info["bottom"] == info["viewH"]))
        print("  系统:", " ".join(info["chips"]), "|", info["nodes"])
        print("  滚动条:", info["ticker"][:120])
        print("  章节 %d 个：" % info["tiles"], info["by"])
        print("  页面里剩下的 envrow:", info["envRowLeft"])
        print("  页面报错:", "; ".join(errors[:3]) if errors else "无")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
