"""The dialog has to say what the run will make.

Open the console, pick the project, open the run dialog, and read what
it says about the frame, the resolution and the style - and whether
the project agrees with it.
"""
import json
import sys
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"

with urllib.request.urlopen(BASE + "/api/projects", timeout=20) as r:
    projects = json.loads(r.read().decode("utf-8")).get("projects") or []
print("  项目：%s" % "、".join(p.get("title", "") for p in projects))
if not projects:
    sys.exit("没有项目")
slug = projects[0].get("slug")

with urllib.request.urlopen(
        BASE + "/api/projects/" + urllib.parse.quote(slug), timeout=20) as r:
    detail = json.loads(r.read().decode("utf-8"))
ad = (detail.get("art_direction") or {})
print("  项目里存的：画幅 %s %sx%s  风格 %s"
      % (ad.get("aspect_ratio"), ad.get("frame_width"),
         ad.get("frame_height"), ad.get("style")))

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000})
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_selector("#projlist .proj", timeout=20000)
    page.click('#projlist .proj[data-slug="%s"]' % slug)
    page.wait_for_timeout(1500)
    # the run button
    btn = page.query_selector("#runGo")
    print("  开始按钮：%s" % (btn is not None))
    if btn:
        btn.click()
        page.wait_for_timeout(2500)
        dlg = page.query_selector("dialog.dk-dialog")
        if dlg:
            print("  弹窗里的内容：")
            for line in dlg.inner_text().split("\n"):
                if line.strip():
                    print("     " + line.strip())
            page.screenshot(path=r"C:\Users\David\AppData\Local\Temp\opencode\preflight.png")
            print("  截图：preflight.png")
        else:
            print("  弹窗没出来")
            page.screenshot(path=r"C:\Users\David\AppData\Local\Temp\opencode\preflight.png")
    browser.close()
