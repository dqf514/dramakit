"""Refresh the handoff note."""
from pathlib import Path

p = Path(r"E:\\dramakit\\rounds\\接力说明.md")
s = p.read_text(encoding="utf-8")

old = """## 三、开机后按这个顺序做"""
new = """## 二之二、3090 已经接进流水线

那台机器（192.168.31.7，双 3090）现在是 **H3 模式常开**，两个 ComfyUI 实例各占一张卡：

| 实例 | 端口 | 显卡 | 容器 |
|---|---|---|---|
| gpu3090-a | 8188 | GPU 0 | `comfyui-h3-a` |
| gpu3090-b | 8189 | GPU 1 | `comfyui-h3-b` |

分工：**5080 只出图**（FLUX 3，nvfp4），**两台 3090 只出视频**（H3 ref2va，
int8/convrot 权重，因为 Ampere 没有 FP4 张量核）。节点池按"在途任务数"均分。

已配好：免密密钥、david 在 docker 组、远端权重齐全、`/data` 还有 1.6T。

**注意**：那台机器原本在跑 Qwen3.8-27B-FP8 的 API 服务（vLLM），显存是分时复用的。
现在 LLM 暂时不用，vLLM 已停；要用回去的时候：

```bash
ssh david@192.168.31.7
docker compose -p dramakit-h3 -f ~/dramakit/docker-compose.h3.yml down
cd /opt/deploy && docker compose up -d vllm
```

## 三、开机后按这个顺序做"""
assert old in s, "锚点没找到"
s = s.replace(old, new, 1)

old = """## 五、还没做完的"""
new = """## 四之二、已经验证过的

- **ref2va 在 5080（nvfp4）和 3090（int8/convrot）上都能说清楚中文**
  （whisper 转写：「我想清楚了」✓）
- **参考音频当音色参考不影响说话**（官方：Audio carries timbre, not words）
- **节点池能把活分到两台机器**：a=5、b=1（第一次跑，均分逻辑是之后补的，
  现在按"在途任务数"分）
- **原生音频路径的每一步都通了**：R2V 提示词 → 参考音频上传 → 片段自带人声 →
  合成时人声取自片段

## 五、还没做完的"""
assert old in s, "锚点2没找到"
s = s.replace(old, new, 1)

old = """- 多模态模型提的**结尾要给对方的反应**：规则已写进分镜提示词，还没有验证的效果
- 竖屏 + 场景母版 + 道具连贯这一版还没有跟原生音频合起来看"""
new = """- 多模态模型提的**结尾要给对方的反应**：规则已写进分镜提示词，还没有验证的效果
- 竖屏 + 场景母版 + 道具连贯这一版还没有跟原生音频合起来看
- **音色一致性还没验**：每一镜都拿同一句录音当音色参考，但不同镜头里听起来
  是不是同一个人，要听一遍才知道
- 原生音频路径下，**同一个角色的不同句子**要拿同一份参考音频（现在拿的是
  这一句自己的录音）——音色参考应该固定成角色的那一份"""
assert old in s, "锚点3没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("接力说明已更新")
