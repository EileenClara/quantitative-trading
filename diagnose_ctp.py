"""
CTP 连接诊断脚本 v2 —— 简洁版，就看 CTP 回调有没有回来
"""
from time import sleep
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine
from vnpy.trader.event import EVENT_LOG, EVENT_ACCOUNT, EVENT_CONTRACT
from vnpy_ctp import CtpGateway


def on_log(event: Event) -> None:
    print(f"[LOG] {event.data.msg}")

def on_account(event: Event) -> None:
    print(f"[ACCOUNT] ✅ 账户数据到达！{event.data.accountid} 余额={event.data.balance}")

def on_contract(event: Event) -> None:
    print(f"[CONTRACT] ✅ 合约数据到达！{event.data.symbol}")

def main():
    print("=== CTP 连接诊断 v2 ===")
    print(f"目标: 182.254.243.31:30001")
    print(f"用户: uskh301")
    print()

    event_engine = EventEngine()
    event_engine.register(EVENT_LOG, on_log)
    event_engine.register(EVENT_ACCOUNT, on_account)
    event_engine.register(EVENT_CONTRACT, on_contract)

    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(CtpGateway)

    setting = {
        "用户名": "uskh301",
        "密码": "qwertyuiop~01",
        "经纪商代码": "9999",
        "交易服务器": "182.254.243.31:30001",
        "行情服务器": "182.254.243.31:30011",
        "产品名称": "simnow_client_test",
        "授权编码": "0000000000000000",
        "产品信息": ""
    }

    main_engine.connect(setting, "CTP")
    print("[*] 已发起连接，等待 CTP 回调...")
    print()

    # 等待 30 秒，看看有什么事件回来
    for i in range(30):
        sleep(1)

    # 检查结果
    print()
    print("=== 30秒后检查 ===")
    accounts = main_engine.get_all_accounts()
    contracts = main_engine.get_all_contracts()
    print(f"账户: {len(accounts)} 个")
    print(f"合约: {len(contracts)} 个")

    if accounts:
        for a in accounts:
            print(f"  ✅ {a.accountid}: 余额={a.balance}")
    else:
        print("  ❌ 没有账户数据返回")
        print()
        print("可能原因：")
        print("  1. SimNow 非交易时段拒绝登录（试试晚上 21:00 后）")
        print("  2. 密码错误或账号未激活")
        print("  3. 第一组服务器挂了，换第二组试试")
        print("  4. 防火墙/杀毒软件拦截了 TCP 连接")

    main_engine.close()


if __name__ == "__main__":
    main()
