"""What the node page looks like, and whether it works.

The page is the config made editable, so it has to show three things at
once: the state of each card, the weights that card is told to load, and
which files it actually has - the last is what makes the model setting
worth having, since a filename typed by hand is a filename the card may
never have heard of.

So the page is opened, the node pool is expanded, and what comes out is
both looked at and saved to a file.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from playwright.sync_api import sync_playwright   # noqa: E402

BASE = "http://127.0.0.1:8080"
SHOT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\nodes_page.png")
out = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1680, "height": 1100})
    errors = []
    page.on("console", lambda m: errors.append(f"{m.type}: {m.text}")
            if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    page.goto(BASE + "/?v=" + str(int(time.time())), wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    # open the node pool page
    btn = page.query_selector('.railbtn[data-page="nodes"]')
    if not btn:
        out.append("**侧栏没有「节点池」按钮**")
    else:
        out.append("侧栏有「节点池」按钮 ✓")
        btn.click()
        page.wait_for_timeout(4000)

    cards = page.query_selector_all("#page-nodes .card[data-node]")
    out.append(f"节点卡片数 {len(cards)}")
    for c in cards:
        name = c.get_attribute("data-node")
        txt = c.inner_text().replace("\n", " | ")[:220]
        out.append(f"  {name}: {txt}")

    # the model dropdowns
    out.append("")
    out.append("=== 模型下拉框 ===")
    sels = page.query_selector_all("#page-nodes select[data-ov]")
    out.append(f"  模型下拉框 {len(sels)} 个")
    for s in sels[:6]:
        opts = s.query_selector_all("option")
        val = s.input_value()
        out.append(f"    当前={val}  可选 {len(opts)} 项")
        holder = s.evaluate("e => e.closest('[data-models]') ? 1 : 0")
        _ = holder

    # the workflow dropdowns
    out.append("")
    out.append("=== 工作流下拉框 ===")
    wsels = page.query_selector_all("#page-nodes select[data-wf]")
    out.append(f"  工作流下拉框 {len(wsels)} 个")
    for s in wsels[:4]:
        opts = s.query_selector_all("option")
        out.append(f"    {s.get_attribute('data-wf')}: {len(opts)} 项")

    # open the settings of the first node
    if cards:
        det = cards[0].query_selector("details")
        if det:
            det.evaluate("e => { e.open = true; }")
            page.wait_for_timeout(3000)
            out.append("")
            out.append("=== 展开后的设置项 ===")
            labels = cards[0].query_selector_all(".fl")
            for l in labels[:8]:
                out.append(f"    {l.inner_text().strip()[:60]}")

    page.screenshot(path=str(SHOT), full_page=False)
    out.append("")
    out.append(f"截图: {SHOT}")

    out.append("")
    out.append("=== 控制台报错 ===")
    out.append("  " + ("\n  ".join(errors[:10]) if errors else "无"))
    browser.close()

SHOT.parent.joinpath("nodepage_report.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
