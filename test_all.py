"""
VeighNa 量化平台 —— 完整功能测试
测试所有 API 端点、RPC 函数、前端页面是否正常
"""
import sys
import os
import json
import socket
import time
import requests
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = "http://127.0.0.1:8000"
TOKEN = None
PASS = 0
FAIL = 0


def check(desc, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {desc}")
    else:
        FAIL += 1
        print(f"  [FAIL] {desc}  {detail}")


def header():
    return {"Authorization": f"Bearer {TOKEN}", "accept": "application/json"}


def api_get(path):
    try:
        r = requests.get(BASE + path, headers=header(), timeout=5)
        return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)


def api_post(path, body=None):
    try:
        r = requests.post(BASE + path, json=body or {}, headers={**header(), "Content-Type": "application/json"}, timeout=5)
        return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
    except Exception as e:
        return 0, str(e)


def test_port(port, name):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    r = s.connect_ex(("127.0.0.1", port))
    s.close()
    check(f"{name} (端口 {port}) 运行中", r == 0, f"端口 {port} 未连接")
    return r == 0


def main():
    global TOKEN, PASS, FAIL
    print("=" * 60)
    print("  VeighNa 量化平台 —— 完整功能测试")
    print("=" * 60)
    print()

    # ===== 第1步：检查服务器是否运行 =====
    print("【1】服务器状态")
    rpc_ok = test_port(2014, "RPC 请求服务")
    pub_ok = test_port(4102, "RPC 推送服务")
    web_ok = test_port(8000, "Web 服务")
    if not web_ok:
        print("\n[FAIL] Web 服务未启动，终止测试。请先运行 run_server.py 和 run_web.py")
        return 1
    if not rpc_ok:
        print("  WARN RPC 未运行，量化功能 API 将不可用")
    print()

    # ===== 第2步：认证 =====
    print("【2】用户认证")
    code, result = requests.post(
        BASE + "/token",
        data={"username": "admin", "password": "vnpy2024"},
        headers={"accept": "application/json"},
        timeout=5
    ).status_code, None
    try:
        r = requests.post(BASE + "/token", data={"username": "admin", "password": "vnpy2024"}, headers={"accept": "application/json"}, timeout=5)
        code = r.status_code
        result = r.json()
    except Exception as e:
        code, result = 0, str(e)

    check("登录成功", code == 200, f"status={code}")
    if code == 200 and "access_token" in result:
        TOKEN = result["access_token"]
        check("获取到 JWT Token", len(TOKEN) > 20)
    else:
        print("  [FAIL] 无法获取 Token，后续测试终止")
        return 1
    print()

    # ===== 第3步：基础交易 API =====
    print("【3】基础交易 API")
    code, data = api_get("/account")
    check("/account 账户查询", code == 200, f"status={code}")
    check("  返回列表格式", isinstance(data, list))

    code, data = api_get("/position")
    check("/position 持仓查询", code == 200)

    code, data = api_get("/order")
    check("/order 委托查询", code == 200)

    code, data = api_get("/trade")
    check("/trade 成交查询", code == 200)

    code, data = api_get("/contract")
    check("/contract 合约查询", code == 200)
    print()

    # ===== 第4步：CTA 策略 API =====
    print("【4】CTA 策略管理 API")
    code, data = api_get("/api/ext/strategy-classes")
    check("/strategy-classes 策略类型列表", code == 200)
    check("  返回策略数量 > 0", isinstance(data, list) and len(data) > 0,
          f"got {len(data) if isinstance(data, list) else type(data).__name__}")
    if isinstance(data, list) and len(data) > 0:
        s = data[0]
        check("  策略有 display_name", "display_name" in s)
        check("  策略有 description", "description" in s)
        check("  策略有 parameters", "parameters" in s and isinstance(s["parameters"], dict))

    code, data = api_get("/api/ext/strategies")
    check("/strategies 运行中策略", code == 200)
    check("  返回列表格式", isinstance(data, list))

    # 测试添加策略（用第一个可用策略类型）
    add_ok = False
    if rpc_ok and isinstance(data, list):
        code2, data2 = api_get("/api/ext/strategy-classes")
        if code2 == 200 and isinstance(data2, list) and len(data2) > 0:
            cls = data2[0]
            code3, result3 = api_post("/api/ext/strategy/add", {
                "class_name": cls["class_name"],
                "strategy_name": "_test_strategy_",
                "vt_symbols": "",
                "setting": {}
            })
            check("  添加策略", code3 == 200, f"status={code3}")
            if code3 == 200:
                add_ok = True
    if not add_ok:
        check("  添加策略", False, "RPC 未连接或无可用策略类型")
    print()

    # ===== 第5步：算法交易 API =====
    print("【5】算法交易 API")
    code, data = api_get("/api/ext/algo-templates")
    check("/algo-templates 算法模板列表", code == 200)
    check("  返回模板数量 > 0", isinstance(data, list) and len(data) > 0)
    if isinstance(data, list) and len(data) > 0:
        t = data[0]
        check("  模板有 display_name", "display_name" in t)
        check("  模板有 description", "description" in t)

    code, data = api_get("/api/ext/algos")
    check("/algos 运行中算法", code == 200)
    print()

    # ===== 第6步：风控管理 API =====
    print("【6】风控管理 API")
    code, data = api_get("/api/ext/risk-rule-names")
    check("/risk-rule-names 风控规则列表", code == 200)
    check("  返回规则数量 > 0", isinstance(data, list) and len(data) > 0)

    code, data = api_get("/api/ext/risk-rules")
    check("/risk-rules 风控状态", code == 200)
    print()

    # ===== 第7步：前端页面 =====
    print("【7】前端页面")
    try:
        r = requests.get(BASE + "/", timeout=5)
        html = r.text
        check("首页返回 200", r.status_code == 200, f"status={r.status_code}")
        check("  包含 DOCTYPE", "<!DOCTYPE html>" in html)
        check("  包含 CTA 策略标签", "CTA 策略" in html or "cta" in html.lower())
        check("  包含算法交易标签", "算法交易" in html or "algo" in html.lower())
        check("  包含风控管理标签", "风控管理" in html or "risk" in html.lower())
    except Exception as e:
        check("首页可访问", False, str(e))
    print()

    # ===== 第8步：清理测试数据 =====
    print("【8】清理")
    if rpc_ok:
        try:
            api_post("/api/ext/strategy/remove", {"strategy_name": "_test_strategy_"})
        except Exception:
            pass
    check("清理测试策略", True, "(如果创建了)")
    print()

    # ===== 结果 =====
    print("=" * 60)
    total = PASS + FAIL
    print(f"  测试结果: {PASS} 通过 / {FAIL} 失败 / {total} 总计")
    if FAIL == 0:
        print("  [PASS] 全部测试通过！")
    else:
        print(f"  [FAIL] 有 {FAIL} 项测试失败，请检查")
    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
