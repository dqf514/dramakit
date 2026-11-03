"""Is there a cu130 PyTorch for this machine, and how big is it?"""
import re
import urllib.request

for m in ("https://mirrors.aliyun.com/pytorch-wheels/cu130/",
          "https://mirror.nju.edu.cn/pytorch/whl/cu130/"):
    try:
        with urllib.request.urlopen(m, timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
        hits = re.findall(r'href="([^"]*torch-[^"]*cp312[^"]*win_amd64[^"]*)"', html)
        print("  %s -> %d 个 cp312 win wheel" % (m, len(hits)))
        for h in sorted(set(x.split("/")[-1] for x in hits))[-8:]:
            print("      ", h)
    except Exception as e:  # noqa: BLE001
        print("  %s -> %s %s" % (m, type(e).__name__, str(e)[:80]))

# what else does the wheel need alongside it
print()
for pkg in ("torchvision", "torchaudio"):
    try:
        with urllib.request.urlopen(
                "https://mirrors.aliyun.com/pytorch-wheels/cu130/", timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
        hits = re.findall(r'href="([^"]*%s-[^"]*cp312[^"]*win_amd64[^"]*)"' % pkg, html)
        print("  %s -> %d" % (pkg, len(hits)))
        for h in sorted(set(x.split("/")[-1] for x in hits))[-4:]:
            print("      ", h)
    except Exception as e:  # noqa: BLE001
        print("  %s -> %s" % (pkg, type(e).__name__))
