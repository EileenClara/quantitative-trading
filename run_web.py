"""
VeighNa WebTrader —— FastAPI Web 服务
启动后访问 http://127.0.0.1:8000/docs 查看 API 文档

使用前请先启动 run_server.py！

用法：python run_web.py
"""
import sys
import os

# 确保能找到当前目录下的配置文件
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from vnpy_webtrader.web import app


def main():
    """启动 FastAPI Web 服务器"""
    print("=" * 60)
    print("  VeighNa WebTrader 启动中...")
    print("=" * 60)
    print()
    print("  启动后访问：")
    print("  · API 文档：  http://127.0.0.1:8000/docs")
    print("  · 交易页面：  http://127.0.0.1:8000/")
    print("  · WebSocket： ws://127.0.0.1:8000/ws/")
    print()
    print("  默认登录账号：admin / vnpy2024")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
