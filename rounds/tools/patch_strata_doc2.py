"""Finish the strata notes: the deployment section still describes the
old machine - one card, shared by two services, sixty gigabytes of
memory. It is two cards now, each with its own service, and a hundred
and twenty-one gigabytes.
"""
import pathlib
import re

p = pathlib.Path("E:/strata-info.md")
t = p.read_text(encoding="utf-8")

lines = t.split("\n")
out = []
for line in lines:
    if line.startswith("- **硬件**"):
        out.append("- **硬件**：121GB RAM / **RTX 3090 ×2 24GB**"
                   "（卡 0 = ComfyUI，卡 1 = Strata）")
    elif line.startswith("- **资源占用**"):
        out.append("- **资源占用**：GPU 显存 ~23.5GB（**卡 1**）、内存约 45GB（模型加载后）")
        out.append("- **容器**：容器名 `strata-engine`，`--restart unless-stopped`"
                   "（崩了或机器重启，它自己回来）；引擎是容器的子进程，"
                   "容器删了引擎也就没了")
    elif line.startswith("- **ComfyUI**"):
        out.append("- **ComfyUI**：**不再和 Strata 抢显存**——它在卡 0"
                   "（`CUDA_VISIBLE_DEVICES=0`），Strata 在卡 1，两个服务可以同时开着。"
                   "启动 `docker start comfyui-h3-a`")
        out.append("- **内存**：两边加起来约 98GB / 121GB，可用约 22GB。"
                   "再加第三个吃内存的东西之前先 `free -g`——之前机器被拖死过一次"
                   "（两个 ComfyUI 实例各 45GB，内核只能杀进程）")
    else:
        out.append(line)

t = "\n".join(out)
p.write_text(t, encoding="utf-8")
print("写好了", p, p.stat().st_size, "字节")
i = t.find("## 部署环境备注")
print()
print(t[i:i + 800])
