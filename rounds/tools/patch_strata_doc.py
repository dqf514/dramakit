"""Bring the strata notes up to date: the machine has two cards now.

The service itself has not changed - same model, same port, same
answers. What changed is where it lives and how it is started: it now
has a card of its own, and it is started from a container because the
engine lives under /root.
"""
import pathlib

p = pathlib.Path("E:/strata-info.md")
t = p.read_text(encoding="utf-8")

pairs = [
    # the machine moved from .7 to .8
    ("192.168.31.7", "192.168.31.8"),
    ("`本机 IP：`192.168.31.8`", "`本机 IP：`192.168.31.8`"),
    # how it is started now
    ("export PATH=\"/root/.local/bin:$PATH\"   # 每个新终端先执行这行\n\n"
     "strata launch --status                    # 查看运行状态\n"
     "strata launch --stop                      # 停止服务",
     "export PATH=\"/root/.local/bin:$PATH\"   # 每个新终端先执行这行\n\n"
     "strata launch --status                    # 查看运行状态\n"
     "strata launch --stop                      # 停止服务\n\n"
     "# 引擎装在 /root 下，david 账号读不到（sudo 要密码），所以用一个\n"
     "# 以 root 身份运行的容器把它拉起来：挂进机器的 /root 和模型数据，\n"
     "# 用主机的网络和显卡，再用 --gpu 1 告诉它只用卡 1。\n"
     "bash /home/david/start-strata.sh           # 启动（已在卡 1 上）"),
    # the hardware line
    ("- **硬件**：Xeon E5-2698 v4 / 60GB RAM / RTX 3090 24GB",
     "- **硬件**：121GB RAM / **RTX 3090 ×2 24GB**（卡 0 = ComfyUI，卡 1 = Strata）"),
    ("- **资源占用**：GPU 显存 ~23.5GB、内存约 46GB（模型加载后）",
     "- **资源占用**：GPU 显存 ~23.5GB（**卡 1**）、内存约 45GB（模型加载后）\n"
     "- **容器**：容器名 `strata-engine`，`--restart unless-stopped`（自己会回来）；"
     "引擎是容器的子进程，容器删了引擎就没了"),
    ("- **ComfyUI**：为 Strata 腾出显存已停止，恢复命令 `docker start comfyui-h3-a`（会争抢显存，建议先 `strata launch --stop`）",
     "- **ComfyUI**：**不再和 Strata 抢显存**——它在卡 0（`CUDA_VISIBLE_DEVICES=0`），"
     "Strata 在卡 1，两个服务可以同时开着。启动 `docker start comfyui-h3-a`\n"
     "- **内存**：两边加起来约 98GB / 121GB，可用约 22GB。再加第三个吃内存的东西之前先 `free -g`"),
]

for old, new in pairs:
    if old in t:
        t = t.replace(old, new)
        print("  改了：", old.split("\n")[0][:60])
    else:
        print("  （没找到，跳过）:", old.split("\n")[0][:60])

# a short section at the top, about the card
marker = "## 服务概览"
if marker in t and "卡 1" not in t.split(marker)[0]:
    t = t.replace(marker,
                  "## 跑在哪张卡上\n\n"
                  "**卡 1**（第二张 3090）。卡 0 是 ComfyUI，出图和出视频。\n"
                  "两边显存互不相干，可以同时开着。\n\n"
                  "## 服务概览", 1)
    print("  加了「跑在哪张卡上」")

p.write_text(t, encoding="utf-8")
print("写好了", p, p.stat().st_size, "字节")
