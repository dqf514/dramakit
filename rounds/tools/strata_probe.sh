#!/usr/bin/env bash
# What the strata engine is, and how it is started.
export PATH="/root/.local/bin:$PATH"

echo "=== strata 在哪 ==="
command -v strata
strata --version 2>&1 | head -3

echo
echo "=== 当前状态 ==="
strata launch --status 2>&1 | head -25

echo
echo "=== launch 的参数（找显卡相关的） ==="
strata launch --help 2>&1 | head -80

echo
echo "=== 预设里存了什么 ==="
ls -la /root/.strata 2>/dev/null | head -20
find /root/.strata /root/.config/strata* -maxdepth 2 -type f 2>/dev/null | head -20
