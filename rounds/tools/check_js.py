"""Find where the added script stops parsing.

The page came up blank with a syntax error, and a syntax error in a
template literal is hard to see by eye - the braces of the markup and the
braces of the interpolation look the same. So the added block is walked
character by character, with the strings set aside, and the first place
the nesting goes wrong is reported with its surroundings.

It also checks the whole script, because a block that is balanced on its
own can still break the file it sits in.
"""
import re
import sys
from pathlib import Path

HTML = Path(r"E:\dramakit\dramakit\web\static\index.html")
text = HTML.read_text(encoding="utf-8")

start = text.index("// ---------- 节点池：远程节点的设置、模型、工作流 ----------")
end = text.index("function stageStateFor", start)
block = text[start:end]


def walk(src: str, label: str) -> None:
    depth_p = depth_b = depth_s = 0
    quote = None
    prev = ""
    line = 1
    for k, ch in enumerate(src):
        if ch == "\n":
            line += 1
        if quote:
            if ch == quote and prev != "\\":
                quote = None
            prev = ch
            continue
        if ch in "`\"'":
            quote = ch
        elif ch == "(":
            depth_p += 1
        elif ch == ")":
            depth_p -= 1
        elif ch == "{":
            depth_b += 1
        elif ch == "}":
            depth_b -= 1
        elif ch == "[":
            depth_s += 1
        elif ch == "]":
            depth_s -= 1
        if depth_p < 0 or depth_b < 0 or depth_s < 0:
            lo = max(0, k - 260)
            print(f"--- {label}: 第 {line} 行，偏移 {k} 处提前闭合 ---")
            print(repr(src[lo:k + 60]))
            return
    print(f"--- {label}: 走完未提前闭合 ( = {depth_p}  {{ = {depth_b}  [ = {depth_s} ---")


print("=== 我新增的块 ===")
walk(block, "新增块")

# --- the whole script ---------------------------------------------------
m = re.search(r"<script>(.*?)</script>", text, re.S)
if m:
    script = m.group(1)
    print()
    print("=== 整个 script ===")
    walk(script, "script")

    # where does my block start inside it?
    off = script.find("// ---------- 节点池")
    print(f"  新增块在 script 中的偏移 {off} / 总长 {len(script)}")
    if off > 0:
        print("  新增块之前:")
        walk(script[:off], "新增块之前")
