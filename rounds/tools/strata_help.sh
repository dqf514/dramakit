#!/usr/bin/env bash
# The launcher's own words about which cards it may use, and what it did
# last time it was started.
set -u
IMG=python:3.12-slim

docker run --rm -v /root:/root:ro -v /data/strata-data:/data/strata-data:ro \
  "$IMG" sh -c '
export PATH=/root/.local/bin:$PATH
echo "=== launch --help（找显卡和上下文） ==="
strata launch --help 2>&1 | head -120
echo
echo "=== 上次的启动日志 ==="
cat /root/strata-launch.log
echo
echo "=== 32k 那个 profile ==="
cat /root/.config/strata/profiles/launch-iq3_xxs-32k.json
' 2>&1 | head -220
