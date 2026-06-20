#!/bin/bash
# ============================================================
# 服务器端一键更新脚本
# 用法：bash update_server.sh
# ============================================================
set -e

cd /opt/quantitative-trading

echo "[1/4] 拉取最新代码..."
git pull

echo "[2/4] 安装新依赖（如有）..."
pip install -r requirements.txt --break-system-packages -q

echo "[3/4] 重启交易引擎..."
kill $(ps aux | grep 'run_server.py' | grep -v grep | awk '{print $2}') 2>/dev/null || true
sleep 3
nohup python3 run_server.py > /var/log/vnpy_server.log 2>&1 &
sleep 12

echo "[4/4] 部署前端并重启 Web..."
python3 -c "
import vnpy_webtrader, os, shutil
d = os.path.dirname(vnpy_webtrader.__file__)
shutil.copy2('trading_dashboard.html', os.path.join(d, 'static', 'index.html'))
print('HTML deployed')
"
kill $(ps aux | grep 'run_web.py' | grep -v grep | awk '{print $2}') 2>/dev/null || true
sleep 2
nohup python3 run_web.py > /var/log/vnpy_web.log 2>&1 &

echo ""
echo "更新完成！访问 http://8.130.10.207:8000"
