import pathlib

t = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html").read_text(
    encoding="utf-8")
for pat in ["wb-setup", "applyStyleSkills", "wb-side", "by_style",
            'class="tick"', "skstep", "这一步不注入技能"]:
    print("  %-20s %d 次" % (pat, t.count(pat)))
print()
i = t.index("function applyStyleSkills")
print(t[i - 60:i + 900])
