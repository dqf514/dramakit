#!/usr/bin/env bash
# What is actually eating the memory on the card machine?
#
# The question is not "how much is it" but "what is holding it" - so
# this asks the machine itself, rather than guessing from the size of
# the model files.
echo "=== 机器有多少内存 ==="
grep -E "MemTotal|MemAvailable|SwapTotal" /proc/meminfo
echo
echo "=== 每个 ComfyUI 进程占了多少 ==="
for c in comfyui-h3-a comfyui-h3-b; do
  pid=$(docker inspect -f '{{.State.Pid}}' "$c" 2>/dev/null)
  [ -z "$pid" ] && continue
  echo "--- $c (pid $pid) ---"
  ps -o rss=,vsz= -p "$pid" 2>/dev/null | awk '{printf "    常驻 %.1f GB  虚拟 %.1f GB\n", $1/1048576, $2/1048576}'
  # the children: the python that actually loads the models
  for p in $(pgrep -P "$pid" 2>/dev/null); do
    ps -o rss= -p "$p" 2>/dev/null | awk -v p="$p" '{printf "    子进程 %s 常驻 %.1f GB\n", p, $1/1048576}'
  done
done
echo
echo "=== 最大的几个进程 ==="
ps -eo rss=,comm= --sort=-rss | head -8 | awk '{printf "  %8.1f GB  %s\n", $1/1048576, $2}'
echo
echo "=== 每个容器里的 python 占了多少 ==="
for c in comfyui-h3-a comfyui-h3-b; do
  echo "--- $c ---"
  docker exec "$c" sh -c "ps -eo rss=,comm= --sort=-rss 2>/dev/null | head -4" 2>/dev/null \
    | awk '{printf "    %8.1f GB  %s\n", $1/1048576, $2}'
done
echo
echo "=== 换了 torch 之后有没有钉住内存 ==="
for c in comfyui-h3-a comfyui-h3-b; do
  echo "--- $c ---"
  docker logs "$c" 2>&1 | grep -iE "pinned memory|async weight|lowvram|reserve" | tail -4 | sed 's/^/    /'
done
