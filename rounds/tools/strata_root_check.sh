#!/usr/bin/env bash
# The engine is installed under /root, which the david user cannot read.
# What can david do, and is the engine there?
echo "=== 我是谁 ==="
id

echo
echo "=== sudo 权限 ==="
sudo -n -l 2>&1 | tail -20

echo
echo "=== /root/.local/bin 能不能看到 ==="
ls -la /root/.local/bin/ 2>&1 | head -20
sudo -n ls -la /root/.local/bin/ 2>&1 | head -20

echo
echo "=== 有没有 strata 的容器镜像（含未标记的） ==="
docker images -a --format '{{.Repository}}:{{.Tag}} | {{.ID}} | {{.Size}}' | head -20

echo
echo "=== 所有容器（含停止的） ==="
docker ps -a --format '{{.Names}} | {{.Image}} | {{.Status}}'

echo
echo "=== /data/strata-data 里有没有启动脚本 ==="
ls -la /data/strata-data/
find /data/strata-data -maxdepth 1 -type f | head

echo
echo "=== .7 上还有没有别的机器 ==="
ip -4 addr show 2>/dev/null | grep inet | head
