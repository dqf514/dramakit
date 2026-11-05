#!/usr/bin/env bash
# What the strata engine says about the last request.
set -u
C=strata-engine
LOG=/root/.local/state/strata/launch/lan.engine.log

echo "--- 引擎日志尾部 ---"
docker exec "$C" sh -c "tail -40 $LOG" 2>&1 | tail -40

echo
echo "--- 有没有 502 / error ---"
docker exec "$C" sh -c "grep -iE 'error|abort|fail|oom|502|crash' $LOG | tail -10" 2>&1 | tail -10

echo
echo "--- 容器内存/占用 ---"
docker stats --no-stream --format '{{.Name}} {{.MemUsage}} {{.CPUPerc}}' strata-engine 2>&1

echo
echo "--- 显存 ---"
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>&1

echo
echo "--- 主机内存 ---"
free -g | head -2
