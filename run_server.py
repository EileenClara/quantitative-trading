"""
VeighNa 交易服务器 —— 连接券商，启动 RPC 服务
让 WebTrader（前端）可以通过 RPC 调用交易功能

用法：python run_server.py
"""
from time import sleep
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine
from vnpy.trader.event import EVENT_LOG
from vnpy.trader.object import LogData

# ====== 交易接口 ======
from vnpy_ctp import CtpGateway            # CTP 期货（SimNow 仿真）

# ====== 本地虚拟交易 ======
from vnpy_paperaccount import PaperAccountApp  # 本地仿真账户，CTP 连上后自动撮合

# ====== 策略模块 ======
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctabacktester import CtaBacktesterApp
from vnpy_datamanager import DataManagerApp

# ====== 算法交易 ======
from vnpy_algotrading import AlgoTradingApp

# ====== 风险管理 ======
from vnpy_riskmanager import RiskManagerApp

# ====== 数据管理 ======
from vnpy_spreadtrading import SpreadTradingApp
from vnpy_datarecorder import DataRecorderApp

# ====== RPC 服务（核心！让 WebTrader 能连进来）======
from vnpy_rpcservice import RpcServiceApp
from vnpy_rpcservice.rpc_service.engine import RpcEngine, EVENT_RPC_LOG

# ====== RPC 扩展（CTA/算法/风控 → Web API）======
from rpc_extensions import register_extensions


def process_log_event(event: Event) -> None:
    """打印日志到控制台"""
    log: LogData = event.data
    msg: str = f"{log.time}\t{log.msg}"
    print(msg)


def main() -> None:
    """启动 VeighNa 交易服务器"""
    print("=" * 60)
    print("  VeighNa 交易服务器启动中...")
    print("=" * 60)

    # 1. 创建事件引擎
    event_engine: EventEngine = EventEngine()
    event_engine.register(EVENT_LOG, process_log_event)
    event_engine.register(EVENT_RPC_LOG, process_log_event)

    # 2. 创建主引擎
    main_engine: MainEngine = MainEngine(event_engine)

    # 3. 添加交易接口
    main_engine.add_gateway(CtpGateway)
    print("[OK] CTP 交易接口已加载")

    # 4. 添加 PaperAccount（本地虚拟账户）
    #    CTP 连上后自动用真实行情模拟成交
    #    初始资金 100 万，下单立即虚拟撮合
    main_engine.add_app(PaperAccountApp)
    print("[OK] PaperAccount 虚拟账户已加载（初始资金 100 万）")

    # 5. 添加策略模块
    main_engine.add_app(CtaStrategyApp)
    main_engine.add_app(CtaBacktesterApp)
    main_engine.add_app(DataManagerApp)
    print("[OK] 策略模块已加载（CTA策略 + 回测 + 数据管理）")

    # 6. 添加算法交易
    main_engine.add_app(AlgoTradingApp)
    print("[OK] 算法交易已加载（TWAP / Iceberg / Sniper / BestLimit）")

    # 7. 添加风险管理
    main_engine.add_app(RiskManagerApp)
    print("[OK] 风控模块已加载")

    # 7b. 添加数据管理 + 行情录制
    main_engine.add_app(SpreadTradingApp)
    main_engine.add_app(DataRecorderApp)
    print("[OK] 数据管理 + 行情录制已加载")

    # 8. 添加 RPC 服务（让 WebTrader 可以通过网络调用）
    rpc_engine: RpcEngine = main_engine.add_app(RpcServiceApp)
    print("[OK] RPC 服务已加载")

    # 9. 注册扩展 RPC 函数（CTA策略/算法/风控 → Web API）
    #    这样前端就能通过 REST API 管理策略、启动算法、设置风控
    register_extensions(main_engine, rpc_engine.server)
    print("[OK] RPC 扩展已注册（策略管理 + 算法交易 + 风控）")

    # 10. ====== 连接 CTP 交易接口（SimNow 仿真） ======
    ctp_setting: dict[str, str] = {
        "用户名": "uskh301",
        "密码": "qwertyuiop~01",
        "经纪商代码": "9999",
        "交易服务器": "182.254.243.31:30001",   # SimNow 第一组 Trade Front
        "行情服务器": "182.254.243.31:30011",   # SimNow 第一组 Market Front
        "产品名称": "simnow_client_test",
        "授权编码": "0000000000000000",
        "产品信息": ""
    }

    print("[*] 正在连接 CTP (SimNow 仿真)...")
    main_engine.connect(ctp_setting, "CTP")
    print("[*] 等待 CTP 连接完成（非交易时段可能无响应，属正常现象）...")
    sleep(10)

    # 11. ====== 启动 RPC 服务器 ======
    rep_address: str = "tcp://*:2014"   # 请求/响应端口
    pub_address: str = "tcp://*:4102"   # 推送/订阅端口
    rpc_engine.start(rep_address, pub_address)

    print("=" * 60)
    print("  RPC 服务器已启动！")
    print(f"  请求端口: {rep_address}")
    print(f"  推送端口: {pub_address}")
    print("  现在可以启动 run_web.py 了")
    print("")
    print("  [!] CTP 交易时段：上午9:00-11:30 | 下午13:30-15:00 | 夜盘21:00起")
    print("  [!] 端午假期：6.19-6.21 休市，6.22 恢复交易")
    print("  [!] 策略/算法功能需要 CTP 连接才能产生真实信号")
    print("=" * 60)

    # 9. 保持运行
    while True:
        sleep(1)


if __name__ == "__main__":
    main()
