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
            {"class_name": "DoubleMaStrategy", "parameters": {"fast_window": 10, "slow_window": 20, "description": "双均线策略"}},
            {"class_name": "AtrRsiStrategy", "parameters": {"atr_length": 26, "atr_ma_length": 10, "rsi_length": 5}},
            {"class_name": "BollChannelStrategy", "parameters": {"boll_window": 26, "boll_dev": 2.0}},
            {"class_name": "DualThrustStrategy", "parameters": {"k1": 0.7, "k2": 0.7, "day_window": 1}},
            {"class_name": "KingKeltnerStrategy", "parameters": {"kk_length": 20, "kk_dev": 2.0}},
            {"class_name": "TurtleSignalStrategy", "parameters": {"entry_window": 20, "exit_window": 10, "atr_window": 20}},
            {"class_name": "MultiSignalStrategy", "parameters": {"ma_window": 10}},
            {"class_name": "MultiTimeframeStrategy", "parameters": {"fast_ma": 5, "slow_ma": 20}},
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
            {"name": "TwapAlgo", "display_name": "TWAP 时间加权均价", "default_setting": {"time": 600}},
            {"name": "IcebergAlgo", "display_name": "Iceberg 冰山指令", "default_setting": {"display_volume": 1, "interval": 3}},
            {"name": "SniperAlgo", "display_name": "Sniper 狙击手", "default_setting": {"interval": 3}},
            {"name": "BestLimitAlgo", "display_name": "BestLimit 最优限价", "default_setting": {"min_volume": 1, "interval": 3}},
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
        return ["order_flow_limit", "order_size_limit", "total_order_limit", "cancel_limit"]


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
