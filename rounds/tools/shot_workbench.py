"""A picture of the workbench, so the layout can be looked at."""
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = r"C:\Users\David\AppData\Local\Temp\opencode\workbench.png"


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1700})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_selector("#projlist .proj", timeout=20000)
        # the first project in the list
        page.click("#projlist .proj")
        page.wait_for_selector("#lookCard", timeout=20000)
        page.wait_for_selector("#page-flow .skck input", timeout=20000)
        page.wait_for_timeout(1200)
        page.screenshot(path=OUT, full_page=True)
        print("  截图:", OUT)
        if errors:
            print("  页面报错:", "; ".join(errors[:3]))
        else:
            print("  页面没有报错")
        # how tall is the page?
        h = page.evaluate("document.body.scrollHeight")
        print("  页面总高:", h, "px")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
