#!/bin/bash
PW=dangyang
echo "=== 历史启动列表 ==="
journalctl --list-boots --no-pager 2>/dev/null | tail -12

echo
echo "=== 每次开机各认出几张 NVIDIA 卡 ==="
for b in $(journalctl --list-boots --no-pager 2>/dev/null | awk '{print $1}' | tac | head -8); do
  n=$(journalctl -b $b -k --no-pager 2>/dev/null | grep -c -E "nvidia [0-9a-f]{8}: (vgaarb|Initializing|Loaded|kernel module)")
  devs=$(journalctl -b $b -k --no-pager 2>/dev/null | grep -o -E "nvidia 0000:[0-9a-f:.]+" | sort -u | tr '\n' ' ')
  first=$(journalctl -b $b --no-pager 2>/dev/null | head -1 | cut -c1-16)
  echo "  boot $b  开始于 $first | 认出的卡: ${devs:-（无）}"
done

echo
echo "=== 上一次开机里关于显卡的报错 ==="
prev=$(journalctl --list-boots --no-pager 2>/dev/null | awk 'NR==2{print $1}')
if [ -n "$prev" ]; then
  echo "  （上一次 boot $prev）"
  journalctl -b $prev -k --no-pager 2>/dev/null | grep -i -E "nvidia|nvrm|pcie.*error|falling off|Xid" | grep -v -E "taint|license|nvlink|uvm|modeset|drm|input:|vgaarb|Initialization" | tail -20
fi

echo
echo "=== 这次开机有没有 PCIe 链路错误 ==="
journalctl -b 0 -k --no-pager 2>/dev/null | grep -i -E "AER: Corrected|AER: Uncorrected|fatal|surprise removal|link down" | head -10 || echo "  没有"

echo
echo "=== 主板型号 / 电源 ==="
cat /sys/class/dmi/id/board_vendor /sys/class/dmi/id/board_name /sys/class/dmi/id/board_version 2>/dev/null
ls /sys/class/power_supply/ 2>/dev/null
for p in /sys/class/power_supply/*/; do
  [ -f "$p/online" ] && echo "  $(basename $p): online=$(cat $p/online 2>/dev/null) power=$(cat $p/power 2>/dev/null)"
done 2>/dev/null
