#!/usr/bin/env bash
# What does the engine need from the machine, and what is on this machine?
set -u
IMG=python:3.12-slim

echo "=== 引擎文件 ==="
docker run --rm -v /root:/root:ro "$IMG" sh -c '
  ls -la /root/.local/share/strata/terminal/current/ 2>/dev/null | head
  echo "--- bin ---"
  ls -la /root/.local/share/strata/terminal/current/bin/ 2>/dev/null | head
  echo "--- python 运行时 ---"
  ls -la /root/.local/share/strata/terminal/current/python/bin/ 2>/dev/null | head -5
  echo "--- 引擎程序 ---"
  find /root/.local/share/strata -maxdepth 4 -type f -size +10M 2>/dev/null | head -10
' 2>&1 | head -40

echo
echo "=== 宿主机有没有 CUDA 运行时 ==="
ls -d /usr/local/cuda* 2>/dev/null
ls /usr/local/cuda/lib64/libcudart* 2>/dev/null | head -3
nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1

echo
echo "=== 引擎链接了哪些库 ==="
docker run --rm -v /root:/root:ro "$IMG" sh -c '
  for f in $(find /root/.local/share/strata -maxdepth 4 -type f -perm -u+x -size +5M 2>/dev/null | head -3); do
    echo "--- $f ---"
    ldd "$f" 2>&1 | grep -iE "not found|cuda|nvidia" | head -12
  done' 2>&1 | head -40
