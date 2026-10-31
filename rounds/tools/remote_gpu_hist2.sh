#!/bin/bash
echo "=== boot -1（10/30 16:02 开机，卡消失的那次）里关于 04:00.0 的一切 ==="
journalctl -b -1 -k --no-pager 2>/dev/null | grep -i -E "04:00|pcieport 0000:00:03|GPU has fallen off|Xid|nvrm.*03:00|nvrm.*04:00|Unknown PCI|device not responding" | head -25

echo
echo "=== boot -1 里 NVIDIA 驱动初始化了几次、认到几张 ==="
journalctl -b -1 -k --no-pager 2>/dev/null | grep -i -E "NVRM: Xid|GPU has fallen off" | tail -8
echo "  驱动加载行数: $(journalctl -b -1 -k --no-pager 2>/dev/null | grep -c 'loading NVIDIA UNIX')"

echo
echo "=== boot -2（10/29，两张卡都好好的）里 04:00.0 的初始化 ==="
journalctl -b -2 -k --no-pager 2>/dev/null | grep -i -E "04:00" | head -8

echo
echo "=== 现在 BIOS 里那个插槽的状态 ==="
dmidecode -t slot 2>/dev/null | grep -B3 -A2 "04:00" | head -20

echo
echo "=== 电源线/PSU 线索：主板与供电 ==="
cat /sys/class/dmi/id/board_vendor /sys/class/dmi/id/board_name 2>/dev/null
echo "  CPU 插槽数: $(grep -c processor /proc/cpuinfo)"
echo "  当前 CPU 数: $(nproc)"
