"""Write the new context into the notes.

The table in the notes says 256K will not fit. That was true when the
machine had sixty gigabytes of memory and both services shared one
card. Now the engine streams its conversation memory - a third of the
cells sit in the card and the rest are read from memory as they are
needed - so the number says how much of the conversation is close at
hand, not what the setting costs.
"""
import pathlib

p = pathlib.Path("E:/strata-info.md")
t = p.read_text(encoding="utf-8")

lines = t.split("\n")
out = []
for line in lines:
    if line.startswith("| **128K + q4_0（当前）**"):
        out.append("| 128K + q4_0 | ~8 GB | 可行，内存增量与 64K int8 相当 |")
        out.append("| **256K + q4_0（当前）** | ~16 GB | **可以**——引擎的 KV 是流式的："
                   "显存里放 32K 格，其余放在内存里按需读，实测 96% 的读取命中显存 |")
    elif line.startswith("| 256K 及以上"):
        out.append("| 256K 默认 int8 | ~32 GB | 不建议：会和出视频的 ComfyUI 抢内存 |")
    elif line.startswith("| 上下文 |"):
        out.append("| 上下文 | **256K tokens**（KV cache 按 q4_0 量化省内存，"
                   "且是**流式**的：显存放 32K 格，其余按需从内存读），支持图片输入（GPU 读取） |")
    else:
        out.append(line)

t = "\n".join(out)

old_step = ("2. 用新参数重启，例如换 64K：`strata launch --preset lan --context 64k --restart`"
            "（或去掉 `--preset` 用完整参数）")
new_step = (old_step + "\n   本机走容器：`docker rm -f strata-engine && bash /home/david/start-strata.sh`"
            "（脚本里已经写了 256k）")
if old_step in t:
    t = t.replace(old_step, new_step)
    print("  加了容器的改法")

note = ("> **现在能上 256K 的原因**：以前这台机器只有 60GB 内存，而且 Strata 和 ComfyUI 共用一张卡，\n"
        "> 上下文一大就没地方放。现在是 121GB 内存、两张卡各一个服务：ComfyUI 占约 48GB、\n"
        "> Strata 占约 45GB，剩下约 14GB 可用；再加上引擎的 KV 是流式的，\n"
        "> 显存放不下的部分不会一次全进内存。\n\n")
marker = "## 健康检查"
if marker in t and "现在能上 256K 的原因" not in t:
    t = t.replace(marker, note + marker, 1)
    print("  加了说明")

t = t.replace('"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "131072"',
              '"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "262144"')
t = t.replace("`CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072`：匹配 Strata 的 128K 上下文",
              "`CLAUDE_CODE_MAX_CONTEXT_TOKENS=262144`：匹配 Strata 的 256K 上下文")
p.write_text(t, encoding="utf-8")
print("写好了", p, p.stat().st_size, "字节")
i = t.find("### 调整上下文")
print()
print(t[i:i + 1100])
