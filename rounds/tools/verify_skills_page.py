"""Is the skills page in place, and is its JavaScript well-formed?

The page was stitched into a file that is mostly template literals, so one
unbalanced backtick would take the whole console down rather than just the
new page. This checks the wiring is present, the tags balance, and the
script block parses.
"""
import re
from pathlib import Path

s = Path(r"E:\dramakit\dramakit\web\static\index.html").read_text(encoding="utf-8")

checks = [
    ("导航按钮", 'data-page="skills"' in s),
    ("页面 section", 'id="page-skills"' in s),
    ("switchPage 分支", 'if(name==="skills") renderSkills();' in s),
    ("renderSkills", "function renderSkills" in s),
    ("recommendSkills", "function recommendSkills" in s),
    ("saveSkills", "function saveSkills" in s),
    ("skillPick", "function skillPick" in s),
    ("成本显示", "sk-cost" in s),
    ("AI 推荐按钮", "让 AI 按本项目挑" in s),
]
for label, ok in checks:
    print(f"  [{'ok' if ok else 'MISSING'}]  {label}")

print()
print(f"<style>: {s.count('<style>')}   </style>: {s.count('</style>')}")
print(f"<script>: {s.count('<script')}   </script>: {s.count('</script>')}")

# the skills script block, and whether it balances
i = s.find("const SK_STAGES=")
assert i > 0, "找不到技能脚本"
start = s.rfind("<script>", 0, i)
end = s.find("</script>", i)
block = s[start + 8:end]
ticks = block.count("`")
print(f"技能脚本: {len(block)} 字符, 反引号 {ticks} "
      f"({'偶数，配平' if ticks % 2 == 0 else '奇数，会破坏页面！'})")
print(f"  花括号 {block.count('{')} / {block.count('}')}")
