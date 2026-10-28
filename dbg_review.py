import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"E:\\dramakit\\projects\\轮次09_09\\review.json"
d = json.load(open(path, encoding="utf-8"))
print("总分:", d.get("总分"))
print("各维度:", d.get("各维度"))
print()
for i, p in enumerate(d.get("最严重的三个问题") or [], 1):
    print(f"{i}. {p.get('问题')}")
    print(f"   镜头: {p.get('出现在哪个镜头')}")
    print(f"   为什么: {str(p.get('为什么是问题'))[:220]}")
    print(f"   流水线: {str(p.get('流水线该改哪里'))[:320]}")
    print()
