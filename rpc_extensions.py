"""
RPC 扩展 —— 把 CTA / 算法 / 风控 引擎的方法注册到 RPC 服务器上，
让 WebTrader 可以通过 RPC 调用这些功能。
"""
from typing import Any
from vnpy.trader.engine import MainEngine
from vnpy.rpc import RpcServer

# 在模块加载时导入所有内置策略（避免 RPC 线程中的 import 问题）
from vnpy_ctastrategy.strategies.double_ma_strategy import DoubleMaStrategy
from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy
from vnpy_ctastrategy.strategies.boll_channel_strategy import BollChannelStrategy
from vnpy_ctastrategy.strategies.dual_thrust_strategy import DualThrustStrategy
from vnpy_ctastrategy.strategies.king_keltner_strategy import KingKeltnerStrategy
from vnpy_ctastrategy.strategies.turtle_signal_strategy import TurtleSignalStrategy
from vnpy_ctastrategy.strategies.multi_signal_strategy import MultiSignalStrategy
from vnpy_ctastrategy.strategies.multi_timeframe_strategy import MultiTimeframeStrategy

BUILTIN_STRATEGY_CLASSES = [
    DoubleMaStrategy, AtrRsiStrategy, BollChannelStrategy,
    DualThrustStrategy, KingKeltnerStrategy, TurtleSignalStrategy,
    MultiSignalStrategy, MultiTimeframeStrategy,
]


def register_extensions(
    main_engine: MainEngine,
    rpc_server: RpcServer
) -> None:
    """
    将各引擎的核心方法注册到 RPC 服务器上。
    注册后 Web 端通过 RpcClient.方法名() 远程调用。
    """

    # ====== 获取各引擎引用 ======
    cta_engine = _get_engine(main_engine, "CtaStrategy")
    algo_engine = _get_engine(main_engine, "AlgoTrading")
    risk_engine = _get_engine(main_engine, "RiskManager")
    backtester_engine = _get_engine(main_engine, "CtaBacktester")
    data_engine = _get_engine(main_engine, "DataManager")
    recorder_engine = _get_engine(main_engine, "DataRecorder")
    portfolio_engine = _get_engine(main_engine, "PortfolioStrategy")
    spread_engine = _get_engine(main_engine, "SpreadTrading")
    option_engine = _get_engine(main_engine, "OptionMaster")
    script_engine = _get_engine(main_engine, "ScriptTrader")

    # ====== CTA 策略引擎 ======
    if cta_engine:

        def rpc_get_strategies() -> list:
            """获取所有已加载的策略实例"""
            result = []
            for name, strategy in cta_engine.strategies.items():
                result.append({
                    "name": name,
                    "class_name": strategy.class_name,
                    "vt_symbols": list(strategy.vt_symbols),
                    "inited": strategy.inited,
                    "trading": strategy.trading,
                    "parameters": strategy.get_parameters(),
                    "variables": strategy.get_variables()
                })
            return result

        def rpc_get_strategy_classes() -> list:
            """获取所有可用策略类型及参数"""
            if not cta_engine.classes:
                _load_builtin_strategies(cta_engine)
            names = cta_engine.get_all_strategy_class_names()
            name_map = {
                "DoubleMaStrategy": ("双均线策略", "快线上穿慢线买入，下穿卖出。最经典的顺势跟踪策略。", "适合有明显趋势的品种，如螺纹钢、铁矿石"),
                "AtrRsiStrategy": ("ATR+RSI 组合策略", "用 ATR 判断波动大小，RSI 判断超买超卖，两者结合过滤假信号。", "适合波动较大的品种，如沪铜、原油"),
                "BollChannelStrategy": ("布林带策略", "价格触及布林带上轨卖出，触及下轨买入，回归中轨平仓。", "适合震荡品种和短线交易，如豆粕、甲醇"),
                "DualThrustStrategy": ("Dual Thrust 日内突破", "基于前 N 日最高最低价计算上下轨，突破上轨做多，下轨做空。", "适合日内波动大的品种，如股指期货、燃油"),
                "KingKeltnerStrategy": ("肯特纳通道策略", "基于 ATR 构建动态通道，突破通道上沿做多，下沿做空。", "适合趋势中带波动的品种"),
                "TurtleSignalStrategy": ("海龟交易策略", "经典趋势跟踪，用唐奇安通道突破入场，ATR 动态计算仓位。", "适合中长线趋势交易，需严格资金管理"),
                "MultiSignalStrategy": ("多信号综合策略", "同时监听多个技术指标的买卖信号，任一发出即执行。", "适合同时关注多个品种，让程序自动盯盘"),
                "MultiTimeframeStrategy": ("多周期共振策略", "大周期判断趋势方向，小周期寻找入场点。方向一致才开仓。", "适合追求高胜率的波段操作"),
            }
            result = []
            for class_name in names:
                params = cta_engine.get_strategy_class_parameters(class_name)
                info = name_map.get(class_name, ("", "", ""))
                result.append({
                    "class_name": class_name,
                    "display_name": info[0] or class_name,
                    "description": info[1] or "",
                    "scenario": info[2] or "",
                    "parameters": params,
                })
            return result

        def rpc_add_strategy(class_name: str, strategy_name: str,
                             vt_symbols: str, setting: dict) -> str:
            """添加策略实例"""
            symbols = [s.strip() for s in vt_symbols.split(",") if s.strip()]
            if not symbols:
                return "ERROR: 请填写交易合约（格式：cu2506.SHFE），不能为空"
            for sym in symbols:
                if "." not in sym:
                    return f"ERROR: 合约代码 {sym} 格式错误，缺少交易所后缀（如 .SHFE .DCE）"
            if class_name not in cta_engine.classes:
                return f"ERROR: 找不到策略类型 {class_name}（可用：{list(cta_engine.classes.keys())[:5]}...），请重启服务器"
            cta_engine.add_strategy(class_name, strategy_name, symbols[0], setting)
            return f"策略 {strategy_name} 已添加"

        def rpc_init_strategy(strategy_name: str) -> str:
            cta_engine.init_strategy(strategy_name)
            return f"策略 {strategy_name} 初始化完成"

        def rpc_start_strategy(strategy_name: str) -> str:
            cta_engine.start_strategy(strategy_name)
            return f"策略 {strategy_name} 已启动"

        def rpc_stop_strategy(strategy_name: str) -> str:
            cta_engine.stop_strategy(strategy_name)
            return f"策略 {strategy_name} 已停止"

        def rpc_remove_strategy(strategy_name: str) -> str:
            cta_engine.remove_strategy(strategy_name)
            return f"策略 {strategy_name} 已移除"

        def rpc_edit_strategy(strategy_name: str, setting: dict) -> str:
            cta_engine.edit_strategy(strategy_name, setting)
            return f"策略 {strategy_name} 参数已更新"

        rpc_server.register(rpc_get_strategies)
        rpc_server.register(rpc_get_strategy_classes)
        rpc_server.register(rpc_add_strategy)
        rpc_server.register(rpc_init_strategy)
        rpc_server.register(rpc_start_strategy)
        rpc_server.register(rpc_stop_strategy)
        rpc_server.register(rpc_remove_strategy)
        rpc_server.register(rpc_edit_strategy)

    # ====== 算法交易引擎 ======
    if algo_engine:

        def rpc_get_algos() -> list:
            """获取所有正在运行的算法"""
            result = []
            for algo_name, algo in algo_engine.algos.items():
                result.append({
                    "name": algo_name,
                    "template_name": algo.template_name,
                    "vt_symbol": algo.vt_symbol,
                    "direction": algo.direction.value if hasattr(algo.direction, 'value') else str(algo.direction),
                    "offset": algo.offset.value if hasattr(algo.offset, 'value') else str(algo.offset),
                    "price": algo.price,
                    "volume": algo.volume,
                    "traded_volume": algo.traded_volume,
                    "status": algo.status.value if hasattr(algo.status, 'value') else str(algo.status),
                })
            return result

        def rpc_get_algo_templates() -> list:
            """获取所有可用算法模板"""
            result = []
            for name, template in algo_engine.algo_templates.items():
                result.append({
                    "name": name,
                    "display_name": getattr(template, 'display_name', name),
                    "default_setting": getattr(template, 'default_setting', {}),
                })
            return result

        def rpc_start_algo(template_name: str, vt_symbol: str, direction: str,
                           offset: str, price: float, volume: float, setting: dict) -> str:
            """启动算法"""
            from vnpy.trader.constant import Direction, Offset
            dir_map = {"多": Direction.LONG, "空": Direction.SHORT}
            off_map = {"开": Offset.OPEN, "平": Offset.CLOSE, "平今": Offset.CLOSETODAY, "平昨": Offset.CLOSEYESTERDAY}
            d = dir_map.get(direction, Direction.LONG)
            o = off_map.get(offset, Offset.OPEN)
            algo_engine.start_algo(template_name, vt_symbol, d, o, price, volume, setting)
            return f"算法 {template_name} 已启动"

        def rpc_stop_algo(algo_name: str) -> str:
            algo_engine.stop_algo(algo_name)
            return f"算法 {algo_name} 已停止"

        def rpc_pause_algo(algo_name: str) -> str:
            algo_engine.pause_algo(algo_name)
            return f"算法 {algo_name} 已暂停"

        def rpc_resume_algo(algo_name: str) -> str:
            algo_engine.resume_algo(algo_name)
            return f"算法 {algo_name} 已恢复"

        rpc_server.register(rpc_get_algos)
        rpc_server.register(rpc_get_algo_templates)
        rpc_server.register(rpc_start_algo)
        rpc_server.register(rpc_stop_algo)
        rpc_server.register(rpc_pause_algo)
        rpc_server.register(rpc_resume_algo)

    # ====== 风控引擎 ======
    if risk_engine:

        def rpc_get_risk_rules() -> list:
            """获取所有风控规则"""
            result = []
            for name, rule in risk_engine.rules.items():
                result.append({
                    "name": name,
                    "enabled": rule.active if hasattr(rule, 'active') else True,
                    "setting": getattr(rule, 'setting', {}),
                })
            return result

        def rpc_get_risk_rule_names() -> list:
            """获取风控规则名称"""
            return risk_engine.get_all_rule_names()

        def rpc_update_risk_rule(rule_name: str, setting: dict) -> str:
            """更新/启停风控规则"""
            rule = risk_engine.rules.get(rule_name)
            if rule:
                if "active" in setting:
                    rule.active = setting["active"]
                if "limit" in setting:
                    rule.setting = rule.setting or {}
                    rule.setting["limit"] = setting["limit"]
            return f"风控规则 {rule_name} 已更新"

        def rpc_add_risk_rule(rule_name: str) -> str:
            """启用风控规则"""
            rule = risk_engine.rules.get(rule_name)
            if rule:
                rule.active = True
            return f"风控规则 {rule_name} 已启用"

        rpc_server.register(rpc_get_risk_rules)
        rpc_server.register(rpc_get_risk_rule_names)
        rpc_server.register(rpc_update_risk_rule)
        rpc_server.register(rpc_add_risk_rule)

    # ====== CTA 回测引擎 ======
    if backtester_engine:
        def rpc_start_backtesting(strategy_class: str, vt_symbol: str, interval: str,
                                   start: str, end: str, capital: int, setting: dict) -> dict:
            backtester_engine.init_datafeed()
            backtester_engine.load_strategy_class_from_module(strategy_class)
            c = backtester_engine.strategy_class
            backtester_engine.start_backtesting(c, vt_symbol, interval, start, end, 0.0, 0.0, 10, 1, capital, setting)
            stats = backtester_engine.get_result_statistics()
            df = backtester_engine.get_result_df()
            return {
                "statistics": stats,
                "curve": [{"date": str(i), "equity": float(df["balance"].iloc[i])}
                          for i in range(len(df))] if df is not None else [],
            }

        def rpc_get_backtest_data(vt_symbol: str, interval: str, start: str, end: str) -> list:
            backtester_engine.init_datafeed()
            data = backtester_engine.get_history_data(vt_symbol, interval, start, end)
            return [{"date": str(d.datetime), "open": d.open_price, "high": d.high_price,
                     "low": d.low_price, "close": d.close_price, "volume": d.volume} for d in data]

        rpc_server.register(rpc_start_backtesting)
        rpc_server.register(rpc_get_backtest_data)

    # ====== 数据管理引擎 ======
    if data_engine:
        def rpc_get_bar_overview() -> list:
            return data_engine.get_bar_overview()

        def rpc_import_csv(filepath: str, symbol: str, exchange: str, interval: str,
                           start: str, end: str) -> str:
            data_engine.import_data_from_csv(filepath, symbol, exchange, interval, start, end)
            return f"导入 {symbol} 数据完成"

        def rpc_export_csv(filepath: str, symbol: str, exchange: str, interval: str,
                           start: str, end: str) -> str:
            data_engine.output_data_to_csv(filepath, symbol, exchange, interval, start, end)
            return f"导出 {symbol} 数据到 {filepath}"

        def rpc_delete_bar(symbol: str, exchange: str, interval: str) -> str:
            data_engine.delete_bar_data(symbol, exchange, interval)
            return f"删除 {symbol} 数据完成"

        rpc_server.register(rpc_get_bar_overview)
        rpc_server.register(rpc_import_csv)
        rpc_server.register(rpc_export_csv)
        rpc_server.register(rpc_delete_bar)

    # ====== 行情录制引擎 ======
    if recorder_engine:
        def rpc_start_recording(vt_symbols: str) -> str:
            symbols = [s.strip() for s in vt_symbols.split(",") if s.strip()]
            for sym in symbols:
                if "." in sym:
                    s, e = sym.split(".")
                    recorder_engine.add_bar_recording(s, e)
            return f"已开始录制 {len(symbols)} 个合约"

        def rpc_stop_recording(vt_symbols: str) -> str:
            symbols = [s.strip() for s in vt_symbols.split(",") if s.strip()]
            for sym in symbols:
                if "." in sym:
                    s, e = sym.split(".")
                    recorder_engine.remove_bar_recording(s, e)
            return f"已停止录制 {len(symbols)} 个合约"

        def rpc_get_recording_status() -> list:
            return list(recorder_engine.bar_recordings.keys()) if hasattr(recorder_engine, 'bar_recordings') else []

        rpc_server.register(rpc_start_recording)
        rpc_server.register(rpc_stop_recording)
        rpc_server.register(rpc_get_recording_status)

    # ====== 组合策略引擎 ======
    if portfolio_engine:
        def rpc_get_portfolio_strategies() -> list:
            result = []
            for name, s in portfolio_engine.strategies.items():
                result.append({"name": name, "class_name": s.class_name, "inited": s.inited, "trading": s.trading,
                               "parameters": s.get_parameters(), "variables": s.get_variables()})
            return result

        def rpc_get_portfolio_classes() -> list:
            names = portfolio_engine.get_all_strategy_class_names()
            return [{"class_name": n, "parameters": portfolio_engine.get_strategy_class_parameters(n)} for n in names]

        def rpc_add_portfolio(class_name: str, strategy_name: str, vt_symbols: str, setting: dict) -> str:
            symbols = [s.strip() for s in vt_symbols.split(",") if s.strip()]
            if not symbols: return "ERROR: 请填写合约"
            portfolio_engine.add_strategy(class_name, strategy_name, ";".join(symbols), setting)
            return f"组合策略 {strategy_name} 已添加"

        def rpc_portfolio_action(action: str, strategy_name: str) -> str:
            getattr(portfolio_engine, action + "_strategy")(strategy_name)
            return f"{action} {strategy_name} 完成"

        rpc_server.register(rpc_get_portfolio_strategies)
        rpc_server.register(rpc_get_portfolio_classes)
        rpc_server.register(rpc_add_portfolio)
        rpc_server.register(rpc_portfolio_action)

    # ====== 价差交易引擎 ======
    if spread_engine:
        def rpc_get_spread_data() -> list:
            result = []
            for name, s in spread_engine.spread_data_engine.spreads.items():
                result.append({"name": name, "legs": [(l.vt_symbol, l.volume) for l in s.legs.values()] if hasattr(s, 'legs') else [],
                               "price": s.price if hasattr(s, 'price') else 0})
            return result

        def rpc_get_spread_positions() -> list:
            return [{"name": k, "volume": v} for k, v in spread_engine.spread_data_engine.spread_pos.items()]

        def rpc_create_spread(name: str, legs: str) -> str:
            # legs: "cu2506.SHFE:1,rb2510.SHFE:-1"
            spread_engine.update_spread_data(name, {})
            return f"价差 {name} 已创建"

        def rpc_start_spread() -> str:
            spread_engine.start()
            return "价差引擎已启动"

        def rpc_stop_spread() -> str:
            spread_engine.stop()
            return "价差引擎已停止"

        rpc_server.register(rpc_get_spread_data)
        rpc_server.register(rpc_get_spread_positions)
        rpc_server.register(rpc_create_spread)
        rpc_server.register(rpc_start_spread)
        rpc_server.register(rpc_stop_spread)

    # ====== 期权引擎 ======
    if option_engine:
        def rpc_get_option_portfolios() -> list:
            return option_engine.get_portfolio_names()

        def rpc_get_option_data(portfolio_name: str) -> dict:
            option_engine.init_portfolio(portfolio_name)
            data = option_engine.get_portfolio(portfolio_name)
            return {"name": portfolio_name, "chains": [], "greeks": {}}

        def rpc_get_underlyings() -> list:
            return option_engine.get_underlying_symbols()

        def rpc_update_option_setting(portfolio_name: str, setting: dict) -> str:
            option_engine.update_portfolio_setting(portfolio_name, setting)
            return f"期权组合 {portfolio_name} 已更新"

        rpc_server.register(rpc_get_option_portfolios)
        rpc_server.register(rpc_get_option_data)
        rpc_server.register(rpc_get_underlyings)
        rpc_server.register(rpc_update_option_setting)

    # ====== 脚本交易引擎 ======
    if script_engine:
        def rpc_script_buy(vt_symbol: str, price: float, volume: int) -> str:
            script_engine.buy(vt_symbol, price, volume)
            return f"买入 {vt_symbol} {volume}手 @ {price}"

        def rpc_script_sell(vt_symbol: str, price: float, volume: int) -> str:
            script_engine.sell(vt_symbol, price, volume)
            return f"卖出 {vt_symbol} {volume}手 @ {price}"

        def rpc_script_short(vt_symbol: str, price: float, volume: int) -> str:
            script_engine.short(vt_symbol, price, volume)
            return f"做空 {vt_symbol} {volume}手 @ {price}"

        def rpc_script_cover(vt_symbol: str, price: float, volume: int) -> str:
            script_engine.cover(vt_symbol, price, volume)
            return f"平空 {vt_symbol} {volume}手 @ {price}"

        def rpc_script_cancel(vt_orderid: str) -> str:
            script_engine.cancel_order(vt_orderid)
            return f"撤单 {vt_orderid}"

        def rpc_script_get_orders() -> list:
            orders = script_engine.get_all_active_orders()
            return [{"vt_orderid": o.vt_orderid, "vt_symbol": o.vt_symbol, "direction": str(o.direction),
                     "price": o.price, "volume": o.volume, "status": str(o.status)} for o in orders]

        rpc_server.register(rpc_script_buy)
        rpc_server.register(rpc_script_sell)
        rpc_server.register(rpc_script_short)
        rpc_server.register(rpc_script_cover)
        rpc_server.register(rpc_script_cancel)
        rpc_server.register(rpc_script_get_orders)


def _load_builtin_strategies(cta_engine: Any) -> None:
    """把 vnpy_ctastrategy 内置的策略类直接注入到引擎"""
    for cls in BUILTIN_STRATEGY_CLASSES:
        cta_engine.classes[cls.__name__] = cls
    print(f"[OK] Injected {len(BUILTIN_STRATEGY_CLASSES)} strategy classes")


def _get_engine(main_engine: MainEngine, app_name: str) -> Any:
    """从 MainEngine 中获取指定 App 的引擎实例"""
    for name, engine in main_engine.engines.items():
        if app_name in name:
            return engine
    return None
