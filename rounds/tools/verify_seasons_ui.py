"""Is the season wiring in the page well-formed?

The panel was stitched into a page that is mostly template literals, so a
single unbalanced backtick would take the whole console down. This checks
the wiring is present and the new block balances, without a browser.
"""
from pathlib import Path

h = Path(r"E:\dramakit\dramakit\web\static\index.html").read_text(encoding="utf-8")
i = h.index("async function loadSeasons")
j = h.index("</body>", i)
block = h[i:j]

checks = [
    ("seasonHtml declared", "const seasonHtml" in h),
    ("seasonHtml placed in page", "${seasonHtml}" in h),
    ("loadSeasons called once", h.count("loadSeasons(") == 2),
    ("start button calls startSeason", 'onclick="startSeason()"' in h),
    ("panel fetches /api/seasons", "/api/seasons?project=" in h),
    ("run passes the season", "season:season" in h),
    ("run uses every stage", "stages:STAGES.slice()" in h),
]
for label, ok in checks:
    print(f"  [{'ok' if ok else 'MISSING'}]  {label}")

print()
ticks = block.count("`")
print(f"new block backticks: {ticks}  ({'even, balanced' if ticks % 2 == 0 else 'ODD - breaks page'})")
print(f"new block braces:    {block.count('{')} / {block.count('}')}")
