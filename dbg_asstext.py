import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1]
p = ProjectStore(Path(r"E:\dramakit\projects") / name).load()
sc = p.episodes[0].scenes[0]
ass = Path(r"E:\dramakit\projects") / name / "subs" / "ep_001.ass"
print("剧本第一场的台词:")
for l in sc.lines:
    print(f"   {l.kind.value:<9} {l.speaker:<8} 「{l.text}」")
print()
print("字幕文件的前 6 条:")
n = 0
for line in ass.read_text(encoding="utf-8").splitlines():
    if line.startswith("Dialogue:"):
        f = line.split(",", 9)
        print(f"   {f[1]} -> {f[2]} [{f[3]}] 「{f[9]}」")
        n += 1
        if n >= 6:
            break
