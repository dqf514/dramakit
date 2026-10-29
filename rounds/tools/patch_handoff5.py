"""Note that the 3090 is off and how to bring it back."""
from pathlib import Path

p = Path(r"E:\\dramakit\\rounds\\接力说明.md")
s = p.read_text(encoding="utf-8")

old = """## 三、开机后按这个顺序做"""
new = """## 二之四、3090 现在是关着的

用户让先关机，所以机器已经停了：两个 ComfyUI 容器停掉并删掉，机器 `shutdown -h now`。
端口 22/8188/8189 都不通 ✓。

**要用的时候开回来**（机器起来之后）：

```bash
ssh david@192.168.31.7
# H3 模式：起两个 ComfyUI（各一张卡）
docker compose -p dramakit-h3 -f ~/dramakit/docker-compose.h3.yml up -d
# 顺便看一眼有没有东西占着显存
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
```

（编组文件在 `~/dramakit/docker-compose.h3.yml`，是 david 自己的目录；
`/opt/deploy` 那份生产用的没动。）

## 三、开机后按这个顺序做"""
assert old in s, "锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("接力说明已更新")
