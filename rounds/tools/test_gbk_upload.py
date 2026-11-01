"""Upload a GBK novel through the real browser, and see what lands on disk.

The bug lived in the page: File.text() decodes as UTF-8 and swaps anything
else for U+FFFD, so a GBK book reached the server already mangled and the
chapter regex found nothing. This drives the actual console - picks the
file, creates the project - then reads the project back from disk to check
the chapters came out whole.
"""
import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
NOVEL = Path(r"C:\Users\David\AppData\Local\Temp\opencode\gbk_novel.txt")
PROJECTS = Path(r"E:\dramakit\projects")
NAME = "编码测试项目"

# start clean, so a leftover cannot make this look like a pass
shutil.rmtree(PROJECTS / NAME, ignore_errors=True)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(BASE, wait_until="networkidle")
    # the create form lives on the guide page, and the console opens on the
    # workbench whenever a project already exists
    page.wait_for_selector('.railbtn[data-page="guide"]', timeout=8000)
    page.click('.railbtn[data-page="guide"]')
    page.wait_for_selector("#gName", timeout=8000)

    page.fill("#gName", NAME)
    page.set_input_files("#gFilePicker", str(NOVEL))
    page.wait_for_timeout(500)
    page.click("#gCreate")
    # catalog runs LLM-free for the split, but give it room
    page.wait_for_timeout(6000)

    result = page.evaluate("""() => {
      const d = S.detail;
      return {
        current: S.current,
        slug: d && d.slug,
        chapters: d && d.meta && (d.meta.chapters||[]).length,
        firstTitles: (d && d.meta ? (d.meta.chapters||[]) : []).slice(0,5)
                        .map(c => "第"+c.index+"章 "+c.title),
      };
    }""")
    b.close()

print("=== 浏览器实测：GBK 小说上传 ===")
print(json.dumps(result, ensure_ascii=False, indent=2))

# and read the truth off disk
root = PROJECTS / (result.get("slug") or NAME)
src = root / "source"
print()
print("=== 落盘 ===")
print("项目目录:", root.name if root.exists() else "不存在")
if (src / "volumes").exists():
    files = sorted((src / "volumes").glob("*.txt"))
    print("章节文件:", len(files), "个")
    for f in files[:5]:
        body = f.read_text(encoding="utf-8")
        print(f"  {f.name}  {len(body)} 字  开头: {body[:24]!r}")
else:
    print("volumes/ 不存在 -> 没切出章节")

# the mangled-text signature: U+FFFD means the encoding was lost
if (src / "cleaned.txt").exists():
    cleaned = (src / "cleaned.txt").read_text(encoding="utf-8")
    print("cleaned.txt:", len(cleaned), "字, 乱码字符", cleaned.count("\ufffd"), "个")

print()
print("页面错误:", errors[:4] if errors else "无")
