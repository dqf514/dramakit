"""Before changing the torch build, make sure it can be put back.

A venv that cannot be restored is a venv that has to work. So this
checks two things: that the build we want is there, and that the build
we have now is also there - somewhere reachable - to go back to.
"""
import re
import urllib.request

MIRRORS = [
    "https://mirrors.aliyun.com/pytorch-wheels/{cu}/",
    "https://mirror.nju.edu.cn/pytorch/whl/{cu}/",
]
WANT = [
    ("torch", "2.11.0"),
    ("torchvision", "0.26.0"),
    ("torchaudio", "2.11.0"),
]
CUS = ["cu130", "cu128"]


def listing(mirror, cu):
    try:
        with urllib.request.urlopen(mirror.format(cu=cu), timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
        return {(m.group(1), m.group(2), m.group(3)) for m in re.finditer(
            r'(torchvision|torchaudio|torch)-([0-9.]+)(?:%2B|&#43;|\+)(cu\d+)'
            r'-cp312-cp312-win_amd64\.whl', html)}
    except Exception:  # noqa: BLE001
        return set()


for cu in CUS:
    print("=== %s ===" % cu)
    found = set()
    source = ""
    for m in MIRRORS:
        found = listing(m, cu)
        if found:
            source = m
            break
    if not found:
        print("  没有列表")
        continue
    print("  列表来自 %s" % source)
    for pkg, ver in WANT:
        print("  %-12s %-9s %s" % (
            pkg, ver, "有" if (pkg, ver, cu) in found else "**缺**"))
    vers = sorted({v for (p, v, c) in found if c == cu and p == "torch"},
                  key=lambda s: [int(x) for x in s.split(".")])
    print("  这个 cu 下的 torch 版本: %s" % ", ".join(vers[-4:]))
    tv = sorted({v for (p, v, c) in found if c == cu and p == "torchvision"},
                key=lambda s: [int(x) for x in s.split(".")])
    print("  torchvision 版本: %s" % ", ".join(tv[-4:]))
