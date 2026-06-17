"""
API 扩展 —— CTA 策略管理 + 算法交易 + 风控管理的 REST 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from jose import jwt
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/api/ext", tags=["量化策略"])

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
    try:
        return get_client().rpc_get_strategies()
    except Exception:
        return []


@router.get("/strategy-classes")
def list_strategy_classes(access: bool = Depends(ext_auth)):
    """可用策略类型"""
    try:
        return get_client().rpc_get_strategy_classes()
    except Exception:
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
    try:
        result = get_client().rpc_add_strategy(req.class_name, req.strategy_name, req.vt_symbols, req.setting)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/strategy/init")
def init_strategy(req: StrategyActionRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_init_strategy(req.strategy_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/strategy/start")
def start_strategy(req: StrategyActionRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_start_strategy(req.strategy_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/strategy/stop")
def stop_strategy(req: StrategyActionRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_stop_strategy(req.strategy_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/strategy/remove")
def remove_strategy(req: StrategyActionRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_remove_strategy(req.strategy_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
    try:
        return get_client().rpc_get_algos()
    except Exception:
        return []


@router.get("/algo-templates")
def list_algo_templates(access: bool = Depends(ext_auth)):
    try:
        return get_client().rpc_get_algo_templates()
    except Exception:
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
    try:
        result = get_client().rpc_start_algo(req.template_name, req.vt_symbol, req.direction, req.offset, req.price, req.volume, req.setting)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/algo/stop")
def stop_algo(req: AlgoActionRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_stop_algo(req.algo_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/algo/pause")
def pause_algo(req: AlgoActionRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_pause_algo(req.algo_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/algo/resume")
def resume_algo(req: AlgoActionRequest, access: bool = Depends(ext_auth)):
    try:
        result = get_client().rpc_resume_algo(req.algo_name)
        return {"status": "success", "message": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
