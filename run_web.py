"""
VeighNa WebTrader —— FastAPI Web 服务
启动后访问 http://127.0.0.1:8000/docs 查看 API 文档

使用前请先启动 run_server.py！

用法：python run_web.py
"""
import sys
import os

# 确保能找到当前目录下的扩展模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from vnpy_webtrader.web import app
from api_extended import router as extended_router, set_rpc_client

# 挂载扩展路由（CTA策略 / 算法交易 / 风控管理）
app.include_router(extended_router)

# 注入 RPC 客户端引用 —— 在 webtrader 启动后自动获取
@app.on_event("startup")
def link_rpc_client():
    """WebTrader 初始化 RPC 客户端后，注入给扩展路由使用"""
    from vnpy_webtrader.web import rpc_client
    set_rpc_client(rpc_client)


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
    print("  新增量化功能 API：")
    print("  · 策略管理：  /api/ext/strategies")
    print("  · 算法交易：  /api/ext/algo-templates")
    print("  · 风控管理：  /api/ext/risk-rules")
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
