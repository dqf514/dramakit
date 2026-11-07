"""Put the real project back, and take the test leftovers away.

The browser rounds make a project of their own every time, and the
"delete everything" tool took the real one with them.  It is in the
recycle bin, and the bin is where a project that is not wanted should
be - not the working folder.
"""
import pathlib
import shutil

PROJ = pathlib.Path(r"E:\dramakit\projects")
TRASH = PROJ / "_trash"

# the real one goes back
for d in sorted(TRASH.iterdir()):
    if d.is_dir() and d.name.startswith("穿成亿万总裁"):
        target = PROJ / d.name
        if target.exists():
            print("  %s 已经在工作目录里了" % d.name)
        else:
            shutil.move(str(d), str(target))
            print("  放回去了：%s" % d.name)

# the test leftovers go away for good
gone = 0
for d in sorted(TRASH.iterdir()):
    if not d.is_dir():
        continue
    if d.name.startswith(("前端十轮模拟", "九十章测试", "轮次0", "编码测试项目")):
        shutil.rmtree(str(d), ignore_errors=True)
        gone += 1
print("  清掉了 %d 个测试残留" % gone)

print("  现在的项目：")
for d in sorted(PROJ.iterdir()):
    if d.is_dir() and d.name != "_trash":
        print("    %s" % d.name)
