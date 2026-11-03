#!/usr/bin/env bash
# Find the strata engine on this machine.
echo "=== 谁有 strata ==="
for d in /root /home/* /usr/local/bin /usr/bin /opt /data; do
  [ -e "$d" ] || continue
  find "$d" -maxdepth 4 \( -name 'strata' -o -name 'strata*' \) -not -path '*/models/*' 2>/dev/null | head -8
done

echo
echo "=== 8080 端口现在是谁 ==="
ss -ltnp 2>/dev/null | grep -E ':(8080|8081)' || echo "  8080 没在监听"

echo
echo "=== 有没有 strata 的服务/进程记录 ==="
ls -la /root/.local/bin/ 2>/dev/null | head -20
ls -la /home/ 2>/dev/null
echo "--- root 家目录 ---"
ls -la /root/ 2>/dev/null | head -25

echo
echo "=== /opt 下面 ==="
ls -la /opt/ 2>/dev/null | head -20

echo
echo "=== systemd 里有没有 strata ==="
systemctl list-unit-files 2>/dev/null | grep -i strata
ls /etc/systemd/system/ 2>/dev/null | grep -iE 'strata|strat'

echo
echo "=== 历史命令里有没有 strata ==="
grep -ih 'strata' /root/.bash_history /home/*/.bash_history 2>/dev/null | tail -20
