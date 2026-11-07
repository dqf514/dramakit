"""The console, ten times over, in a browser.

The pipeline simulation (`simulate_console.py`) drives the server over
HTTP.  This one drives the *page*: it opens the console, picks a project,
turns the picture round and chooses the style, ticks the skills of every
step, and then asks the server what it thinks happened.  Ten times.

The page is where the choices are made, so this is where a wrong answer
would live: a ratio that does not take, a style that is not written down,
a skill that lands in the wrong column, a save that says it worked and
did not.

    python rounds/tools/browser_rounds.py            # against 127.0.0.1:8760
    python rounds/tools/browser_rounds.py --url http://127.0.0.1:8760
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get(base: str, path: str):
    with urllib.request.urlopen(base + urllib.parse.quote(path, safe="/?=&"),
                                timeout=30) as resp:
        return json.loads(resp.read())


def post(base: str, path: str, body: dict):
    data = json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8760")
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--keep", action="store_true",
                    help="keep the project it makes")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    from playwright.sync_api import sync_playwright

    base = args.url.rstrip("/")
    looks = get(base, "/api/looks")
    styles = looks["styles"]

    # a project of its own: the console is not to be disturbed
    name = f"前端十轮模拟-{int(__import__('time').time())}"
    up = post(base, "/api/upload", {
        "name": name, "file": "十轮.txt",
        "text": "第一章 归来\n傍晚，林远拖着行李走出旧城车站。\n"
                "他听见熟悉的声音，转身望向车站入口。\n"})
    slug = up["slug"]

    failures: list[str] = []
    checks = 0

    def check(what: str, ok: bool, detail: str = "") -> bool:
        nonlocal checks
        checks += 1
        if not ok:
            failures.append(f"{what}" + (f" —— {detail}" if detail else ""))
        return bool(ok)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text)
                if m.type == "error" else None)
        # the pool asks before it takes a card out; the check says yes
        page.on("dialog", lambda d: d.accept())

        for i in range(args.rounds):
            errors.clear()
            ratio = "9:16" if i % 2 == 0 else "16:9"
            page.goto(base, wait_until="domcontentloaded")
            page.wait_for_selector("#projlist .proj", timeout=20000)
            # pick the project
            page.click(f'#projlist .proj[data-slug="{slug}"]')
            page.wait_for_selector("#lookCard", timeout=20000)
            page.wait_for_selector("#page-flow .skck input", timeout=20000)

            # ---- the picture round ------------------------------------ #
            page.click(f'#arRow .seg[data-ar="{ratio}"]')
            sizes = page.eval_on_selector_all(
                "#lookSize option", "els=>els.map(e=>e.value)")
            want = sizes[i % len(sizes)]
            page.select_option("#lookSize", want)
            style = styles[i % len(styles)]
            page.select_option("#lookStyle", style["id"])
            with page.expect_response(
                    lambda r: "/api/project/look" in r.url, timeout=20000) as ri:
                page.click("#lookSave")
            body = ri.value.json()
            check(f"第{i+1}轮 保存画幅与风格", bool(body.get("ok")), str(body)[:160])
            # the page says so out loud
            try:
                page.wait_for_selector("#toast.show.ok", timeout=5000)
                toast_text = page.inner_text("#toast")
            except Exception:  # noqa: BLE001
                toast_text = ""
            check(f"第{i+1}轮 页面说了保存成功", "已保存" in toast_text, toast_text)
            check(f"第{i+1}轮 画幅写对了",
                  (body.get("frame") or {}).get("aspect_ratio") == ratio,
                  str(body.get("frame")))
            w, h = want.split("x")
            check(f"第{i+1}轮 分辨率写对了",
                  (body.get("frame") or {}).get("width") == int(w)
                  and (body.get("frame") or {}).get("height") == int(h),
                  f"{body.get('frame')} 要的是 {want}")

            # the page agrees with the server
            detail = get(base, f"/api/projects/{slug}")
            ad = detail.get("art_direction") or {}
            check(f"第{i+1}轮 项目里存的是这个画幅",
                  ad.get("aspect_ratio") == ratio
                  and ad.get("frame_width") == int(w)
                  and ad.get("frame_height") == int(h),
                  f"{ad.get('aspect_ratio')} {ad.get('frame_width')}x"
                  f"{ad.get('frame_height')}")
            check(f"第{i+1}轮 项目里存的是这个风格",
                  ad.get("style_prompt_prefix") == style["prompt"],
                  f"{ad.get('style_prompt_prefix')!r} 要的是 {style['prompt']!r}")

            # ---- the skills, column by column ------------------------ #
            # the four stages that take skills, and the genre card's own
            # column, in the order they appear
            stages = page.eval_on_selector_all(
                "#page-flow .skck input",
                "els=>Array.from(new Set(els.map(e=>e.dataset.skstage)))")
            check(f"第{i+1}轮 四列技能和类型栏都在", len(stages) == 5, str(stages))
            for stage in stages:
                boxes = page.locator(
                    f'#page-flow .skck input[data-skstage="{stage}"]')
                n = boxes.count()
                if not n:
                    check(f"第{i+1}轮 {stage} 这一列有技能", False, "一格都没有")
                    continue
                # tick the first one that is not ticked; untick it again if
                # they are all ticked already
                idx, name_of = 0, None
                for i in range(n):
                    if not boxes.nth(i).is_checked():
                        idx = i
                        break
                else:
                    idx = 0
                name_of = boxes.nth(idx).get_attribute("data-sk")
                action = "取消" if boxes.nth(idx).is_checked() else "勾上"
                with page.expect_response(
                        lambda r: "/api/skills/save" in r.url,
                        timeout=20000) as ri:
                    boxes.nth(idx).click()
                saved = ri.value.json()
                check(f"第{i+1}轮 {stage} 技能保存成功",
                      bool(saved.get("ok")), str(saved)[:160])
                sel = saved.get("selection") or {}
                after = get(base, f"/api/skills?project={slug}")["selection"]
                check(f"第{i+1}轮 {stage} {action}「{name_of}」存住了",
                      (name_of in (sel.get(stage) or []))
                      == (name_of in (after.get(stage) or [])),
                      f"存的是 {sel.get(stage)}")
                # the box on the page shows what the server now believes
                want_checked = name_of in (after.get(stage) or [])
                again = page.locator(
                    f'#page-flow .skck input[data-skstage="{stage}"]'
                    f'[data-sk="{name_of}"]')
                shown = None
                for _ in range(20):
                    page.wait_for_timeout(100)
                    if again.count() == 1:
                        shown = again.first.is_checked()
                        if shown == want_checked:
                            break
                check(f"第{i+1}轮 {stage} 勾选框和服务器一致",
                      shown == want_checked,
                      f"框是 {shown}，服务器是 {want_checked}；这一列现在是 "
                      + str([(boxes.nth(k).get_attribute('data-sk'),
                              boxes.nth(k).is_checked())
                             for k in range(boxes.count())])[:400])

            # the page has no errors to show
            check(f"第{i+1}轮 页面没有报错", not errors, "; ".join(errors[:3]))
            print(f"· 第{i+1}轮 {ratio} {want} · {style['name']}"
                  f" —— {checks} 项检查，{len(failures)} 项不通过", flush=True)

        # ---- the node pool, added and taken out by hand --------------- #
        # The pool is the list of cards in the config file.  A card is
        # added here, changed and taken out again - and the cards that
        # were there before are still there afterwards.
        errors.clear()
        page.goto(base, wait_until="domcontentloaded")
        page.wait_for_selector('.railbtn[data-page="nodes"]', timeout=20000)
        page.click('.railbtn[data-page="nodes"]')
        page.wait_for_selector("#nodeList", timeout=20000)
        # the cards are looked for on the machine: a card that is not
        # answering takes its time, and the page waits for the lot
        page.wait_for_selector("#nodeList .card", timeout=90000)
        page.wait_for_timeout(500)
        before = [n["name"] for n in get(base, "/api/nodes")["nodes"]]
        check("节点池 页面上有节点", len(before) >= 1, str(before))

        name = f"probe-{int(time.time())}"
        page.click("#nodeAdd")
        page.wait_for_selector('#nodeList [data-nf="name"]', timeout=10000)
        # the settings of a card are behind a fold: open them all
        page.evaluate(
            "()=>document.querySelectorAll('#nodeList details')"
            ".forEach(d=>d.open=true)")
        # the new card is the one that has a name field
        new_card = page.locator("#nodeList .card").filter(
            has=page.locator('[data-nf="name"]'))
        check("节点池 点添加出来一张新卡片", new_card.count() == 1,
              f"{new_card.count()} 张")
        new_card.locator('[data-nf="name"]').fill(name)
        new_card.locator('[data-nf="base_url"]').fill("http://127.0.0.1:8188")
        new_card.locator('[data-nf="roles"]').fill("i2v")
        with page.expect_response(
                lambda r: "/api/nodes/save" in r.url, timeout=20000) as ri:
            new_card.locator("[data-save]").click()
        saved = ri.value.json()
        check("节点池 新增一台节点", bool(saved.get("ok")), str(saved)[:160])
        after = [n["name"] for n in get(base, "/api/nodes")["nodes"]]
        check("节点池 新增的节点在列表里了", name in after, str(after))
        check("节点池 原来的节点一个都没少", set(before) <= set(after),
              f"{before} -> {after}")
        page.wait_for_selector(f'#nodeList [data-node="{name}"]', timeout=10000)
        check("节点池 新增的节点在页面上",
              page.locator(f'#nodeList [data-node="{name}"]').count() == 1)

        # change it
        page.evaluate(
            "()=>document.querySelectorAll('#nodeList details')"
            ".forEach(d=>d.open=true)")
        card = page.locator(f'#nodeList [data-node="{name}"]')
        card.locator('[data-nf="base_url"]').fill("http://127.0.0.1:8199")
        with page.expect_response(
                lambda r: "/api/nodes/save" in r.url, timeout=20000) as ri:
            card.locator("[data-save]").click()
        saved = ri.value.json()
        check("节点池 改一台节点", bool(saved.get("ok")), str(saved)[:160])
        card = next((n for n in get(base, "/api/nodes")["nodes"]
                     if n["name"] == name), None)
        check("节点池 改过的地址存住了",
              bool(card) and card["config"]["base_url"] == "http://127.0.0.1:8199",
              str((card or {}).get("config", {}).get("base_url")))

        # and take it out again
        page.wait_for_selector(f'#nodeList [data-node="{name}"]', timeout=10000)
        page.evaluate(
            "()=>document.querySelectorAll('#nodeList details')"
            ".forEach(d=>d.open=true)")
        card = page.locator(f'#nodeList [data-node="{name}"]')
        with page.expect_response(
                lambda r: "/api/nodes/save" in r.url, timeout=20000) as ri:
            card.locator("[data-del]").click()
        saved = ri.value.json()
        check("节点池 删掉一台节点", bool(saved.get("ok")), str(saved)[:160])
        left = [n["name"] for n in get(base, "/api/nodes")["nodes"]]
        check("节点池 删掉的节点不在列表里了", name not in left, str(left))
        check("节点池 删掉一台不影响别的", set(before) <= set(left),
              f"{before} -> {left}")
        check("节点池 页面没有报错", not errors, "; ".join(errors[:3]))
        print(f"· 节点池 —— {checks} 项检查，{len(failures)} 项不通过", flush=True)

        browser.close()

    if not args.keep:
        try:
            post(base, "/api/projects/delete", {"project": slug})
        except Exception as e:  # noqa: BLE001
            print(f"（项目 {slug} 没删掉：{e}）")

    print("\n" + "=" * 68)
    print(f"{args.rounds} 轮，{checks} 项检查，{len(failures)} 项不通过")
    for f in failures:
        print(f"  ✗ {f}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
