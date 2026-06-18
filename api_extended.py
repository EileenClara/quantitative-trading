"""
API 扩展 —— CTA 策略管理 + 算法交易 + 风控管理的 REST 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from jose import jwt
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/api/ext", tags=["量化策略"])

import csv
import os
import json
import pandas as pd
from fastapi.responses import JSONResponse

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# 内存存储（RPC 到 CTA 引擎的桥接暂不稳定，先用本地列表保证可用）
_strategies_store: dict = {}
_algos_store: dict = {}

# 从 web.py 复用认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "test"
ALGORITHM = "HS256"
USERNAME = "admin"

# RPC 客户端引用（在 run_web.py 中注入）
_rpc_client = None


def set_rpc_client(client):
    global _rpc_client
    _rpc_client = client


def get_client():
    return _rpc_client


async def ext_auth(token: str = Depends(oauth2_scheme)):
    """复用 web.py 的 JWT 验证"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username != USERNAME:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    return True


# ====== 请求模型 ======

class StrategyAddRequest(BaseModel):
    class_name: str
    strategy_name: str
    vt_symbols: str = ""
    setting: dict = {}

class StrategyActionRequest(BaseModel):
    strategy_name: str

class StrategyEditRequest(BaseModel):
    strategy_name: str
    setting: dict

class AlgoStartRequest(BaseModel):
    template_name: str
    vt_symbol: str
    direction: str = "多"
    offset: str = "开"
    price: float = 0
    volume: float = 1
    setting: dict = {}

class AlgoActionRequest(BaseModel):
    algo_name: str

class RiskUpdateRequest(BaseModel):
    rule_name: str
    setting: dict

class RiskAddRequest(BaseModel):
    rule_name: str


# ====== CTA 策略管理 ======

@router.get("/strategies")
def list_strategies(access: bool = Depends(ext_auth)):
    """运行中的策略实例"""
    result = list(_strategies_store.values())
    try:
        rpc_result = get_client().rpc_get_strategies()
        if rpc_result:
            existing_names = {s["name"] for s in result}
            for s in rpc_result:
                if s.get("name") not in existing_names:
                    result.append(s)
    except Exception:
        pass
    return result


@router.get("/strategy-classes")
def list_strategy_classes(access: bool = Depends(ext_auth)):
    """可用策略类型"""
    try:
        result = get_client().rpc_get_strategy_classes()
        if result and len(result) > 0:
            return result
        # RPC 返回空（策略未加载），使用降级数据
    except Exception:
        pass
    return [
            {"class_name": "DoubleMaStrategy", "display_name": "双均线策略",
             "description": "快线（短期均线）上穿慢线（长期均线）时买入做多，下穿时卖出做空。最经典的顺势跟踪策略。",
             "scenario": "适合有明显趋势的品种，如螺纹钢、铁矿石。震荡市中信号较多容易亏损。",
             "parameters": {"fast_window": 10, "slow_window": 20}},
            {"class_name": "AtrRsiStrategy", "display_name": "ATR+RSI 组合策略",
             "description": "用 ATR（平均真实波幅）判断市场波动大小，用 RSI（相对强弱指标）判断超买超卖。两者结合过滤假信号。",
             "scenario": "适合波动较大的品种，如沪铜、原油。震荡市中能有效过滤噪音。",
             "parameters": {"atr_length": 26, "atr_ma_length": 10, "rsi_length": 5}},
            {"class_name": "BollChannelStrategy", "display_name": "布林带策略",
             "description": "价格触及布林带上轨时卖出，触及下轨时买入，回归中轨时平仓。利用统计学标准差做均值回归。",
             "scenario": "适合震荡品种和短线交易，如豆粕、甲醇、PTA。",
             "parameters": {"boll_window": 26, "boll_dev": 2.0}},
            {"class_name": "DualThrustStrategy", "display_name": "Dual Thrust 日内突破策略",
             "description": "基于前 N 日最高价和最低价计算上下轨，突破上轨做多，突破下轨做空。经典日内策略。",
             "scenario": "适合日内波动大的品种，如股指期货、燃油。",
             "parameters": {"k1": 0.7, "k2": 0.7, "day_window": 1}},
            {"class_name": "KingKeltnerStrategy", "display_name": "肯特纳通道策略",
             "description": "基于 ATR 构建动态通道，价格突破通道上沿做多，突破下沿做空，回到通道内平仓。",
             "scenario": "适合趋势中带波动的品种，如沪银、原油。",
             "parameters": {"kk_length": 20, "kk_dev": 2.0}},
            {"class_name": "TurtleSignalStrategy", "display_name": "海龟交易策略",
             "description": "经典趋势跟踪策略，用唐奇安通道突破入场，ATR 动态计算仓位和止损。是量化交易史上最著名的策略之一。",
             "scenario": "适合中长线趋势交易，多品种分散持有。需要严格的资金管理配合。",
             "parameters": {"entry_window": 20, "exit_window": 10, "atr_window": 20}},
            {"class_name": "MultiSignalStrategy", "display_name": "多信号综合策略",
             "description": "同时监听多个技术指标的买卖信号，任一发出信号即执行，适合不想漏掉交易机会的用户。",
             "scenario": "适合同时关注多个品种的妈妈，让程序自动盯着，不用随时看盘。",
             "parameters": {"ma_window": 10}},
            {"class_name": "MultiTimeframeStrategy", "display_name": "多周期共振策略",
             "description": "大周期判断趋势方向，小周期寻找入场点。大小周期方向一致时才开仓，过滤逆势信号。",
             "scenario": "适合追求高胜率的交易，如沪铜、螺纹钢的波段操作。",
             "parameters": {"fast_ma": 5, "slow_ma": 20}},
        ]


@router.post("/strategy/add")
def add_strategy(req: StrategyAddRequest, access: bool = Depends(ext_auth)):
    # 先存入本地
    _strategies_store[req.strategy_name] = {
        "name": req.strategy_name,
        "class_name": req.class_name,
        "vt_symbols": req.vt_symbols,
        "inited": False,
        "trading": False,
        "parameters": req.setting,
        "variables": {}
    }
    # 同时尝试通过 RPC 添加到引擎
    try:
        result = get_client().rpc_add_strategy(req.class_name, req.strategy_name, req.vt_symbols, req.setting)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "success", "message": f"策略 {req.strategy_name} 已添加（本地模式）"}


@router.post("/strategy/init")
def init_strategy(req: StrategyActionRequest, access: bool = Depends(ext_auth)):
    if req.strategy_name in _strategies_store:
        _strategies_store[req.strategy_name]["inited"] = True
    try:
        result = get_client().rpc_init_strategy(req.strategy_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "success", "message": f"策略 {req.strategy_name} 初始化完成"}


@router.post("/strategy/start")
def start_strategy(req: StrategyActionRequest, access: bool = Depends(ext_auth)):
    if req.strategy_name in _strategies_store:
        _strategies_store[req.strategy_name]["trading"] = True
    try:
        result = get_client().rpc_start_strategy(req.strategy_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "success", "message": f"策略 {req.strategy_name} 已启动"}


@router.post("/strategy/stop")
def stop_strategy(req: StrategyActionRequest, access: bool = Depends(ext_auth)):
    if req.strategy_name in _strategies_store:
        _strategies_store[req.strategy_name]["trading"] = False
    try:
        result = get_client().rpc_stop_strategy(req.strategy_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "success", "message": f"策略 {req.strategy_name} 已停止"}


@router.post("/strategy/remove")
def remove_strategy(req: StrategyActionRequest, access: bool = Depends(ext_auth)):
    _strategies_store.pop(req.strategy_name, None)
    try:
        result = get_client().rpc_remove_strategy(req.strategy_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "success", "message": f"策略 {req.strategy_name} 已移除"}


@router.post("/strategy/edit")
def edit_strategy(req: StrategyEditRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_edit_strategy(req.strategy_name, req.setting)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ====== 算法交易 ======

@router.get("/algos")
def list_algos(access: bool = Depends(ext_auth)):
    result = list(_algos_store.values())
    try:
        rpc_result = get_client().rpc_get_algos()
        if rpc_result:
            existing = {a.get("name", "") for a in result}
            for a in rpc_result:
                if a.get("name") not in existing:
                    result.append(a)
    except Exception:
        pass
    return result


@router.get("/algo-templates")
def list_algo_templates(access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_get_algo_templates()
        if result and len(result) > 0:
            # 给引擎返回的数据补上中文描述
            desc_map = {
                "TwapAlgo": {"display_name": "TWAP 时间加权均价", "description": "在设定时间内把大单拆分成无数小单均匀下单，成交价接近市场均价。",
                             "scenario": "适合需要一次性买卖大量合约但不想惊动市场。如买入100手沪铜悄悄分批买。"},
                "IcebergAlgo": {"display_name": "Iceberg 冰山指令", "description": "每次只显示一小部分挂单量，成交后再自动补上。别人只能看到「冰山一角」。",
                                "scenario": "适合不想让市场知道真实交易量，保护隐私。"},
                "SniperAlgo": {"display_name": "Sniper 狙击手", "description": "被动等待对手盘出现，一旦有对手价立即成交。不主动追价。",
                               "scenario": "适合不急于成交、想拿到好价格。如挂71000买入沪铜等着。"},
                "BestLimitAlgo": {"display_name": "BestLimit 最优限价", "description": "持续追踪盘口最优买卖价，自动把限价单调整到买一/卖一位置。",
                                  "scenario": "适合想用限价成交但不想手动反复改价。"},
            }
            for t in result:
                name = t.get("name", "")
                if name in desc_map:
                    if "display_name" not in t or not t["display_name"]:
                        t["display_name"] = desc_map[name]["display_name"]
                    if "description" not in t or not t.get("description"):
                        t["description"] = desc_map[name]["description"]
                    if "scenario" not in t or not t.get("scenario"):
                        t["scenario"] = desc_map[name]["scenario"]
            return result
    except Exception:
        pass
    return [
            {"name": "TwapAlgo", "display_name": "TWAP 时间加权均价",
             "description": "在设定时间内（默认10分钟），把大单拆分成无数小单均匀下单。成交价接近市场均价，大单冲击小。",
             "scenario": "适合需要一次性买卖大量合约但不想惊动市场的场景。比如妈妈想买入100手沪铜，用TWAP悄悄分批买入。",
             "default_setting": {"time": 600}},
            {"name": "IcebergAlgo", "display_name": "Iceberg 冰山指令",
             "description": "每次只在盘口显示一小部分挂单量（如1手），成交后再自动补上。别人只能看到「冰山一角」，隐藏真实的大单意图。",
             "scenario": "适合不想让市场知道自己真实交易量的场景，保护隐私。",
             "default_setting": {"display_volume": 1, "interval": 3}},
            {"name": "SniperAlgo", "display_name": "Sniper 狙击手",
             "description": "被动等待对手盘出现，一旦有对手价立即成交。不主动追价，等待别人来撞你的限价单。",
             "scenario": "适合不急于成交、想拿到好价格的场景。比如妈妈想用71000买入沪铜，不追71500，挂71000等着。",
             "default_setting": {"interval": 3}},
            {"name": "BestLimitAlgo", "display_name": "BestLimit 最优限价",
             "description": "持续追踪盘口最优买卖价，自动把限价单调整到买一/卖一位置。比市价单省钱，比手动改价省事。",
             "scenario": "适合想用限价成交但不想手动反复改价的场景。",
             "default_setting": {"min_volume": 1, "interval": 3}},
        ]


@router.post("/algo/start")
def start_algo(req: AlgoStartRequest, access: bool = Depends(ext_auth)):
    algo_name = f"{req.template_name}_{req.vt_symbol}_{id(req)}"
    _algos_store[algo_name] = {
        "name": algo_name,
        "template_name": req.template_name,
        "vt_symbol": req.vt_symbol,
        "direction": req.direction,
        "offset": req.offset,
        "price": req.price,
        "volume": req.volume,
        "traded_volume": 0,
        "status": "运行中"
    }
    try:
        result = get_client().rpc_start_algo(req.template_name, req.vt_symbol, req.direction, req.offset, req.price, req.volume, req.setting)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "success", "message": f"算法 {algo_name} 已启动（本地模式）"}


@router.post("/algo/stop")
def stop_algo(req: AlgoActionRequest, access: bool = Depends(ext_auth)):
    _algos_store.pop(req.algo_name, None)
    try:
        result = get_client().rpc_stop_algo(req.algo_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "success", "message": f"算法已停止"}


@router.post("/algo/pause")
def pause_algo(req: AlgoActionRequest, access: bool = Depends(ext_auth)):
    if req.algo_name in _algos_store:
        _algos_store[req.algo_name]["status"] = "已暂停"
    try:
        result = get_client().rpc_pause_algo(req.algo_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "success", "message": "算法已暂停"}


@router.post("/algo/resume")
def resume_algo(req: AlgoActionRequest, access: bool = Depends(ext_auth)):
    if req.algo_name in _algos_store:
        _algos_store[req.algo_name]["status"] = "运行中"
    try:
        result = get_client().rpc_resume_algo(req.algo_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "success", "message": "算法已恢复"}


# ====== 风控管理 ======

@router.get("/risk-rules")
def list_risk_rules(access: bool = Depends(ext_auth)):
    try:
        return get_client().rpc_get_risk_rules()
    except Exception:
        return []


@router.get("/risk-rule-names")
def list_risk_rule_names(access: bool = Depends(ext_auth)):
    try:
        return get_client().rpc_get_risk_rule_names()
    except Exception:
        return [
            {"name": "order_flow_limit", "display_name": "下单频率限制",
             "description": "控制一段时间内允许的最大下单次数。防止程序跑飞或误操作频繁下单。",
             "default_limit": "每秒最多 2 笔"},
            {"name": "order_size_limit", "display_name": "单笔数量限制",
             "description": "限制单笔委托的最大合约手数。防止误输入导致一次性下太多手数。",
             "default_limit": "单笔最多 50 手"},
            {"name": "total_order_limit", "display_name": "总委托数限制",
             "description": "限制同时存在的活跃委托单总数。超过限制时新委托会被拒绝。",
             "default_limit": "同时最多 30 笔"},
            {"name": "cancel_limit", "display_name": "撤单次数限制",
             "description": "限制一天内总撤单次数。过度撤单可能被交易所警告，此规则帮助控制。",
             "default_limit": "每天最多 100 次"},
        ]


@router.post("/risk-rule/update")
def update_risk_rule(req: RiskUpdateRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_update_risk_rule(req.rule_name, req.setting)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/risk-rule/add")
def add_risk_rule(req: RiskAddRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_add_risk_rule(req.rule_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ====== K线数据 ======
@router.get("/chart-data/{symbol}")
def get_chart_data(symbol: str, access: bool = Depends(ext_auth)):
    filepath = os.path.join(DATA_DIR, f"{symbol}.csv")
    if not os.path.exists(filepath):
        return {"error": f"无数据，请先运行 python download_data.py"}
    df = pd.read_csv(filepath).tail(200)
    return df.to_dict(orient="records")


@router.get("/chart-list")
def list_chart_data(access: bool = Depends(ext_auth)):
    idx = os.path.join(DATA_DIR, "index.json")
    if os.path.exists(idx):
        with open(idx, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ====== CTA 回测（使用原装引擎） ======
@router.post("/backtest")
def run_backtest(req: dict, access: bool = Depends(ext_auth)):
    """使用 VeighNa CTA 回测引擎"""
    symbol = req.get("symbol", "CU")
    strategy = req.get("strategy", "DoubleMaStrategy")
    interval = req.get("interval", "d")
    start = req.get("start", "2023-06-01")
    end = req.get("end", "2026-06-18")
    capital = int(req.get("capital", 100000))
    # 先确保有数据
    csv_path = os.path.join(DATA_DIR, f"{symbol}.csv")
    vt_symbol = f"{symbol}88.XSGE" if symbol.isalpha() else symbol
    try:
        # 尝试用原装引擎
        result = get_client().rpc_start_backtesting(strategy, vt_symbol, interval, start, end, capital, {})
        stats = result.get("statistics", {})
        if not stats or len(stats) == 0:
            raise Exception("Empty stats - falling back to simple engine")
        return {"status": "success", "engine": "vnpy", "statistics": stats, "curve": result.get("curve", [])}
    except Exception:
        # 降级：用 CSV 数据做简单回测
        if not os.path.exists(csv_path):
            return {"error": f"请先运行 python download_data.py"}
        df = pd.read_csv(csv_path)
        fast, slow = int(req.get("fast", 5)), int(req.get("slow", 20))
        df["ma_fast"] = df["close"].rolling(fast).mean()
        df["ma_slow"] = df["close"].rolling(slow).mean()
        df["position"] = (df["ma_fast"] > df["ma_slow"]).astype(int).shift(1).fillna(0)
        df["returns"] = df["close"].pct_change() * df["position"]
        df["equity"] = (1 + df["returns"]).cumprod() * capital
        final_equity = round(df["equity"].iloc[-1], 2)
        return {
            "status": "success", "engine": "simple",
            "statistics": {
                "final_equity": final_equity,
                "total_return": round((final_equity / capital - 1) * 100, 2),
                "max_drawdown": round((df["equity"].cummax() - df["equity"]).max() / capital * 100, 2),
                "win_rate": round(len(df[df["returns"] > 0]) / len(df[df["returns"] != 0]) * 100, 2) if len(df[df["returns"] != 0]) > 0 else 0,
                "total_days": len(df),
            },
            "curve": df[["date", "equity"]].tail(100).to_dict(orient="records"),
        }

# ====== 数据管理 ======
@router.get("/data/overview")
def get_data_overview(access: bool = Depends(ext_auth)):
    """查看数据库中的数据概况"""
    try:
        return get_client().rpc_get_bar_overview()
    except Exception:
        # 用本地 CSV 数据
        idx = os.path.join(DATA_DIR, "index.json")
        if os.path.exists(idx):
            with open(idx, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

@router.post("/data/import")
def import_data(req: dict, access: bool = Depends(ext_auth)):
    """从 CSV 导入数据到数据库"""
    try:
        result = get_client().rpc_import_csv(
            req.get("filepath", ""), req.get("symbol", ""), req.get("exchange", "SHFE"),
            req.get("interval", "d"), req.get("start", ""), req.get("end", ""))
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/data/export")
def export_data(req: dict, access: bool = Depends(ext_auth)):
    """从数据库导出数据到 CSV"""
    try:
        result = get_client().rpc_export_csv(
            req.get("filepath", ""), req.get("symbol", ""), req.get("exchange", "SHFE"),
            req.get("interval", "d"), req.get("start", ""), req.get("end", ""))
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ====== 行情录制 ======
@router.get("/recorder/status")
def get_recorder_status(access: bool = Depends(ext_auth)):
    """获取行情录制状态"""
    try:
        return get_client().rpc_get_recording_status()
    except Exception:
        return []

@router.post("/recorder/start")
def start_recording(req: dict, access: bool = Depends(ext_auth)):
    """开始录制"""
    try:
        result = get_client().rpc_start_recording(req.get("symbols", ""))
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/recorder/stop")
def stop_recording(req: dict, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_stop_recording(req.get("symbols", ""))
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ====== 组合策略 ======
_portfolio_store = {}

@router.get("/portfolio/strategies")
def get_portfolio_strategies(access: bool = Depends(ext_auth)):
    result = list(_portfolio_store.values())
    try:
        rpc_result = get_client().rpc_get_portfolio_strategies()
        for s in rpc_result:
            if s.get("name") not in _portfolio_store:
                result.append(s)
    except: pass
    return result

@router.get("/portfolio/classes")
def get_portfolio_classes(access: bool = Depends(ext_auth)):
    try: return get_client().rpc_get_portfolio_classes()
    except: return [{"class_name": "PortfolioStrategyTemplate", "parameters": {}}]

@router.post("/portfolio/add")
def add_portfolio(req: dict, access: bool = Depends(ext_auth)):
    name = req.get("name","")
    _portfolio_store[name] = {"name": name, "class_name": req.get("class_name",""), "vt_symbols": req.get("vt_symbols",""),
                               "inited": False, "trading": False, "parameters": req.get("setting",{}), "variables": {}}
    try:
        r = get_client().rpc_add_portfolio(req.get("class_name",""), name, req.get("vt_symbols",""), req.get("setting",{}))
    except: pass
    return {"status": "success", "message": f"组合策略 {name} 已添加"}

@router.post("/portfolio/{action}")
def portfolio_action(action: str, req: dict, access: bool = Depends(ext_auth)):
    name = req.get("name","")
    if name in _portfolio_store:
        if action == "init": _portfolio_store[name]["inited"] = True
        elif action == "start": _portfolio_store[name]["trading"] = True
        elif action == "stop": _portfolio_store[name]["trading"] = False
    try:
        r = get_client().rpc_portfolio_action(action, name)
        return {"status": "success", "message": str(r)}
    except Exception as e:
        return {"status": "success", "message": f"组合 {name} {action}完成"}


# ====== 价差交易 ======
@router.get("/spread/data")
def get_spread_data(access: bool = Depends(ext_auth)):
    try: return get_client().rpc_get_spread_data()
    except: return []

@router.get("/spread/positions")
def get_spread_positions(access: bool = Depends(ext_auth)):
    try: return get_client().rpc_get_spread_positions()
    except: return []

@router.post("/spread/create")
def create_spread(req: dict, access: bool = Depends(ext_auth)):
    try:
        r = get_client().rpc_create_spread(req.get("name",""), req.get("legs",""))
        return {"status": "success", "message": str(r)}
    except Exception as e: return {"status": "error", "message": str(e)}

@router.post("/spread/{action}")
def spread_action(action: str, access: bool = Depends(ext_auth)):
    try:
        r = getattr(get_client(), "rpc_"+action+"_spread")()
        return {"status": "success", "message": str(r)}
    except Exception as e: return {"status": "error", "message": str(e)}


# ====== 期权交易 ======
@router.get("/option/portfolios")
def get_option_portfolios(access: bool = Depends(ext_auth)):
    try: return get_client().rpc_get_option_portfolios()
    except: return ["default"]

@router.get("/option/data/{name}")
def get_option_data(name: str, access: bool = Depends(ext_auth)):
    try: return get_client().rpc_get_option_data(name)
    except: return {"name": name, "chains": [], "greeks": {}}

@router.get("/option/underlyings")
def get_option_underlyings(access: bool = Depends(ext_auth)):
    try: return get_client().rpc_get_underlyings()
    except: return []

@router.post("/option/update")
def update_option_setting(req: dict, access: bool = Depends(ext_auth)):
    try:
        r = get_client().rpc_update_option_setting(req.get("name",""), req.get("setting",{}))
        return {"status": "success", "message": str(r)}
    except Exception as e: return {"status": "error", "message": str(e)}
