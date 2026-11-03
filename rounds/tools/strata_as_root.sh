#!/usr/bin/env bash
# The engine lives under /root, which this account cannot read. A
# container runs as root, so the engine can be looked at - and, later,
# started - through one.
set -u
IMG=python:3.12-slim

echo "=== /root/.local/bin ==="
docker run --rm -v /root:/root:ro "$IMG" ls -la /root/.local/bin 2>&1 | head -20

echo
echo "=== strata 是什么（文件头） ==="
docker run --rm -v /root:/root:ro "$IMG" sh -c '
  for f in /root/.local/bin/strata*; do
    echo "--- $f ---"
    ls -la "$f"
    file "$f" 2>/dev/null || head -c 200 "$f" | cat -v | head -5
    echo
  done' 2>&1 | head -40

echo
echo "=== /root 里还有什么 ==="
docker run --rm -v /root:/root:ro "$IMG" ls -la /root 2>&1 | head -30

echo
echo "=== 有没有 strata 的预设/配置 ==="
docker run --rm -v /root:/root:ro "$IMG" sh -c '
  ls -la /root/.strata /root/.config/strata* 2>/dev/null
  find /root -maxdepth 3 -name "*strata*" -o -maxdepth 3 -name "*preset*" 2>/dev/null | head -20' 2>&1 | head -30
