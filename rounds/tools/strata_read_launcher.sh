#!/usr/bin/env bash
# Read the strata launcher and its presets through a container, which runs
# as root and can see /root.
set -u
IMG=python:3.12-slim

docker run --rm -v /root:/root:ro "$IMG" sh -c '
echo "=== launcher 全文 ==="
cat /root/.local/bin/strata
echo
echo "=== 预设 ==="
ls -la /root/.config/strata/launch-presets/
for f in /root/.config/strata/launch-presets/*; do
  echo "--- $f ---"
  cat "$f"
  echo
done
echo "=== settings.json ==="
cat /root/.config/strata/settings.json
echo
echo "=== profiles ==="
find /root/.config/strata/profiles -maxdepth 2 | head -20
echo
echo "=== 上次是怎么起的（launch log） ==="
cat /root/strata-launch.log
' 2>&1 | head -220
