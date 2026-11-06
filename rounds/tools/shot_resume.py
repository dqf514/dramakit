"""The button that picks a run back up.

    python rounds/tools/shot_resume.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\resume.png")


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
        page.wait_for_selector("#runResume", timeout=20000)
        page.wait_for_timeout(3000)

        info = page.evaluate("""() => {
          const b=document.getElementById('runResume');
          const g=document.getElementById('runGo');
          return {text:b?.textContent.trim(), disabled:b?.disabled, title:b?.title,
                  nextTo:b&&g? Math.abs(b.getBoundingClientRect().left-g.getBoundingClientRect().right)<40:false};
        }""")
        print("  续跑按钮:", info["text"], " 禁用:", info["disabled"])
        print("  紧挨着开始按钮:", info["nextTo"])
        print("  提示:", info["title"])

        # what does the project say it can resume?
        with urllib.request.urlopen(BASE + "/api/projects/" + urllib.parse.quote(slug),
                                    timeout=20) as r:
            d = json.loads(r.read())
        last = (d.get("project") or d).get("meta", {}).get("last_run") or {}
        print("  项目记下的计划:", json.dumps(last, ensure_ascii=False)[:160])

        # the task list has one on every run that stopped
        page.click('.wb-tab:has-text("任务")')
        page.wait_for_timeout(2500)
        rows = page.evaluate("""() => {
          const rs=[...document.querySelectorAll('.job-row')];
          return {rows:rs.length, resume:document.querySelectorAll('[data-job-resume]').length};
        }""")
        print("  任务列表: %d 条，其中带续跑 %d 条" % (rows["rows"], rows["resume"]))

        # and the button on the workbench: a run is going, so it must say so
        page.click('.wb-tab:has-text("流程")')
        page.wait_for_timeout(1500)
        page.click("#runResume")
        page.wait_for_timeout(2500)
        toast = page.evaluate("document.querySelector('#toast')?.textContent.trim()")
        print("  点续跑 →", toast or "（没有提示）")
        page.screenshot(path=str(OUT))
        print("  截图:", OUT)
        print("  页面报错:", "; ".join(errors[:3]) if errors else "无")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
