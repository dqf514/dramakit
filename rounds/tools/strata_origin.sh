#!/usr/bin/env bash
# Where does the strata engine come from? It is not installed on this
# machine - only its model data is - so it has to be found or fetched.
echo "=== /opt/deploy/README.md 里提 strata 的地方 ==="
grep -inE 'strata|iq3|iq_pack|引擎|engine' /opt/deploy/README.md | head -30

echo
echo "=== 全盘搜提到 strata 的文件（排除模型数据） ==="
grep -rlI 'strata' /opt /etc /usr/local /root /home /data/models 2>/dev/null | head -20

echo
echo "=== 有没有 iq_pack.py 这类工具 ==="
find / -maxdepth 6 -name 'iq_pack.py' -o -maxdepth 6 -name 'tools' -type d -path '*strata*' 2>/dev/null | head

echo
echo "=== 8080 是不是被别的服务占了（历史记录） ==="
grep -riE 'strata' /opt/deploy/*.sh /opt/deploy/*.yml 2>/dev/null | head -20

echo
echo "=== download-model.sh 里有什么 ==="
head -40 /opt/deploy/download-model.sh

echo
echo "=== 能不能连到 .7 那台机器 ==="
ping -c 2 -W 2 192.168.31.7 2>&1 | tail -3
curl -s --max-time 6 http://192.168.31.7:8080/health 2>&1 | head -3
curl -s --max-time 6 http://192.168.31.7:8080/v1/models 2>&1 | head -5
