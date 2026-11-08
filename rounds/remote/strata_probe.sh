#!/usr/bin/env bash
# What the strata engine was told to do, and what it can be told.
set -u
C=strata-engine

echo "--- launch 配置 ---"
docker exec "$C" sh -c 'cat /root/.local/state/strata/launch/lan.json' 2>&1 | head -50

echo
echo "--- launch 的内存/并发相关选项 ---"
docker exec "$C" sh -c 'export PATH=/root/.local/bin:$PATH; strata launch --help' 2>&1 \
  | grep -iE 'context|parallel|batch|expert|cache|memory|kv|mlock|resident|vram|threads' \
  | head -30
