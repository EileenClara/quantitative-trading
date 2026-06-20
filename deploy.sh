#!/bin/bash
# ============================================================
# VeighNa 量化交易平台 — 一键部署脚本
# 在 Ubuntu 服务器上运行：bash deploy.sh
# ============================================================
set -e

echo "============================================"
echo "  VeighNa 量化交易平台 部署脚本"
echo "============================================"

# 1. 更新系统
echo "[1/7] 更新系统..."
apt update -y && apt upgrade -y

# 2. 安装 Python 3.12 + pip
echo "[2/7] 安装 Python..."
apt install -y python3.12 python3.12-venv python3-pip

# 3. 安装防火墙
echo "[3/7] 配置防火墙..."
apt install -y ufw
ufw allow 22/tcp
ufw allow 8000/tcp
ufw --force enable
echo "防火墙已开放端口: 22 (SSH), 8000 (Web)"

# 4. 下载项目
echo "[4/7] 下载项目..."
cd /opt
git clone https://github.com/EileenClara/quantitative-trading.git || (cd quantitative-trading && git pull)
cd quantitative-trading

# 5. 安装 Python 依赖
echo "[5/7] 安装 Python 依赖（可能需要几分钟）..."
pip install -r requirements.txt --break-system-packages

# 6. 下载历史数据
echo "[6/7] 下载历史数据..."
python3 download_data.py

# 7. 启动服务
echo "[7/7] 启动交易引擎 + Web 服务..."
# 启动交易引擎（后台运行）
nohup python3 run_server.py > /var/log/vnpy_server.log 2>&1 &
# 等 RPC 启动
sleep 15
# 启动 Web 服务（后台运行）
nohup python3 run_web.py > /var/log/vnpy_web.log 2>&1 &

echo ""
echo "============================================"
echo "  部署完成！"
echo ""
echo "  访问地址: http://8.130.10.207:8000"
echo "  默认账号: admin / vnpy2024"
echo ""
echo "  查看日志:"
echo "    tail -f /var/log/vnpy_server.log"
echo "    tail -f /var/log/vnpy_web.log"
echo ""
echo "  重启服务:"
echo "    cd /opt/quantitative-trading"
echo "    nohup python3 run_server.py > /var/log/vnpy_server.log 2>&1 &"
echo "    nohup python3 run_web.py > /var/log/vnpy_web.log 2>&1 &"
echo "============================================"
