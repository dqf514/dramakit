"""A look at the workbench when the book has a lot of chapters.

Eighty-six chapters is where the page stopped fitting: the chapter
list grew until the steps were off the screen.  This makes a book with
ninety chapters, opens the console on it, and says what the page looks
like - three columns, the chapters in the icon view, and nothing taller
than it needs to be.

    python rounds/tools/shot_chapters.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\chapters.png")
N = 90


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def make_book() -> str:
    name = "九十章测试-%d" % __import__("time").time()
    body = {"name": name, "file": "九十章.txt"}
    parts = []
    for i in range(1, N + 1):
        text = ("第%d章 这是第%d章的内容。" % (i, i)) + "风从走廊尽头吹过来，他把灯拧亮了一点。" * 30
        parts.append("第%d章 %s\n%s" % (i, "长夜", text))
    body["text"] = "\n\n".join(parts)
    up = post("/api/upload", body)
    return up["slug"]


def main() -> int:
    slug = make_book()
    print("  造了个项目:", slug, N, "章")
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

        # what does the page say about itself?
        info = page.evaluate("""() => {
          const setup=document.querySelector('.wb-setup');
          const cards=[...setup.children].map(c=>({
            id:c.id||c.className,
            w:Math.round(c.getBoundingClientRect().width),
            h:Math.round(c.getBoundingClientRect().height)}));
          const body=document.querySelector('.chap-body');
          const tiles=document.querySelectorAll('#chapterList .chap-tile');
          const boxes=document.querySelectorAll('#chapterList input[type=checkbox]');
          const sk=document.querySelector('.skcard');
          const opts=document.querySelector('.skopts');
          return {
            cards,
            tiles:tiles.length, boxes:boxes.length,
            chapH:body?Math.round(body.getBoundingClientRect().height):0,
            chapScroll:body?Math.round(body.scrollHeight):0,
            skH:sk?Math.round(sk.getBoundingClientRect().height):0,
            skCols:opts?getComputedStyle(opts).columnCount:0,
            pageH:document.body.scrollHeight,
            viewH:window.innerHeight};
        }""")
        print("  三列:", [(c["id"], c["w"], c["h"]) for c in info["cards"]])
        print("  章节区: 高 %d，内容 %d（滚动=%s）" %
              (info["chapH"], info["chapScroll"], info["chapScroll"] > info["chapH"]))
        print("  图标 %d 个 / 勾选框 %d 个（默认应是图标）" % (info["tiles"], info["boxes"]))
        print("  技能列: 高 %s，勾选框 %s 列" % (info["skH"], info["skCols"]))
        print("  页面高 %d / 视口 %d（一屏=%s）" %
              (info["pageH"], info["viewH"], info["pageH"] <= info["viewH"]))

        # click a tile: it should be picked, not open the reader
        before = page.evaluate("document.querySelectorAll('#chapterList .chap-tile.on').length")
        page.click("#chapterList .chap-tile:nth-child(3)")
        page.wait_for_timeout(400)
        after = page.evaluate("document.querySelectorAll('#chapterList .chap-tile.on').length")
        print("  点一个图标: 选中 %d -> %d（应 -1）" % (before, after))

        # the list view has to scroll inside itself, not push the page down
        page.click("#chapMode")
        page.wait_for_timeout(600)
        lst = page.evaluate("""() => {
          const b=document.querySelector('.chap-body');
          const r=b.getBoundingClientRect();
          return {h:Math.round(r.height), content:Math.round(b.scrollHeight),
                  rows:document.querySelectorAll('#chapterList input[type=checkbox]').length,
                  pageH:document.body.scrollHeight, viewH:window.innerHeight};
        }""")
        print("  列表视图: %d 行，高 %d 内容 %d（内部滚动=%s） 页面高 %d/%d"
              % (lst["rows"], lst["h"], lst["content"],
                 lst["content"] > lst["h"], lst["pageH"], lst["viewH"]))
        page.screenshot(path=str(OUT))
        page.click("#chapMode")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT))
        print("  页面报错:", "; ".join(errors[:3]) if errors else "无")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
