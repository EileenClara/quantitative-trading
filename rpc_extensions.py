"""
RPC 扩展 —— 把 CTA / 算法 / 风控 引擎的方法注册到 RPC 服务器上，
让 WebTrader 可以通过 RPC 调用这些功能。
"""
from typing import Any
from vnpy.trader.engine import MainEngine
from vnpy.rpc import RpcServer


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
            # 如果引擎还没加载策略，先加载内置策略
            if not cta_engine.classes:
                _load_builtin_strategies(cta_engine)
            names = cta_engine.get_all_strategy_class_names()
            result = []
            for class_name in names:
                params = cta_engine.get_strategy_class_parameters(class_name)
                result.append({
                    "class_name": class_name,
                    "parameters": params
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


def _load_builtin_strategies(cta_engine: Any) -> None:
    """把 vnpy_ctastrategy 内置的策略文件加载到引擎中"""
    import vnpy_ctastrategy, os, importlib
    from pathlib import Path
    strat_dir = Path(os.path.dirname(vnpy_ctastrategy.__file__)) / "strategies"
    if not strat_dir.exists():
        print(f"[WARN] Strategy dir not found: {strat_dir}")
        return
    for f in sorted(strat_dir.glob("*_strategy.py")):
        mod_name = f.stem
        full_name = f"vnpy_ctastrategy.strategies.{mod_name}"
        mod = importlib.import_module(full_name)
        cta_engine.load_strategy_class_from_module(mod)
        print(f"[OK] Loaded strategy: {mod_name}")


def _get_engine(main_engine: MainEngine, app_name: str) -> Any:
    """从 MainEngine 中获取指定 App 的引擎实例"""
    for name, engine in main_engine.engines.items():
        if app_name in name:
            return engine
    return None
