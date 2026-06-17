"""
前端逻辑验证 —— 模拟浏览器行为，检查风控开关到底为什么不联动
"""
import json
import re
import requests

BASE = "http://127.0.0.1:8000"
TOKEN = None
PASS = FAIL = 0

def check(desc, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1; print(f"  [OK] {desc}")
    else:
        FAIL += 1; print(f"  [FAIL] {desc}  {detail}")

def login():
    global TOKEN
    r = requests.post(f"{BASE}/token", data={"username":"admin","password":"vnpy2024"},
                      headers={"accept":"application/json"}, timeout=5)
    TOKEN = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOKEN}", "accept":"application/json"}

def api_get(path):
    try:
        r = requests.get(f"{BASE}{path}", headers=login(), timeout=5)
        return r.status_code, r.json()
    except Exception as e:
        return 0, str(e)

def api_post(path, body):
    try:
        r = requests.post(f"{BASE}{path}", json=body, headers={**login(), "Content-Type":"application/json"}, timeout=5)
        return r.status_code, r.json()
    except Exception as e:
        return 0, str(e)

print("=" * 60)
print("  前端风控逻辑端到端测试")
print("=" * 60)

# 1. 获取当前风控状态
print("\n1. 初始状态（GET /api/ext/risk-rules）")
code, rules = api_get("/api/ext/risk-rules")
check("API 返回 200", code == 200, f"code={code}")
check("返回是列表", isinstance(rules, list))
check("返回了规则", len(rules) > 0, f"got {len(rules)} rules")

if rules:
    first_rule = rules[0]
    check("规则有 name 字段", "name" in first_rule)
    check("规则有 enabled 字段", "enabled" in first_rule)
    print(f"    → 第一条规则: name={first_rule.get('name')}, enabled={first_rule.get('enabled')}")

# 2. 模拟前端 toggleRiskRule：关闭第一条规则
if rules:
    print(f"\n2. 模拟前端关闭「{first_rule['name']}」")
    old_enabled = first_rule["enabled"]

    if old_enabled:
        # 模拟 enabled=true → 前端调 update 关闭
        code2, result = api_post("/api/ext/risk-rule/update",
            {"rule_name": first_rule["name"], "setting": {"active": False}})
        check("POST update 返回 200", code2 == 200, f"code={code2}")
        check("返回 status=success", result.get("status") == "success", f"result={result}")
    else:
        # 模拟 enabled=false → 前端调 add 启用
        code2, result = api_post("/api/ext/risk-rule/add",
            {"rule_name": first_rule["name"]})
        check("POST add 返回 200", code2 == 200, f"code={code2}")
        check("返回 status=success", result.get("status") == "success", f"result={result}")

# 3. 验证状态确实变了（模拟 loadRiskRules 重新获取）
print(f"\n3. 验证状态变化（GET /api/ext/risk-rules）")
code3, rules3 = api_get("/api/ext/risk-rules")
check("API 返回 200", code3 == 200)

if rules3:
    first_after = rules3[0]
    if rules and first_rule["name"] == first_after["name"]:
        new_enabled = first_after["enabled"]
        changed = new_enabled != old_enabled
        check(f"enabled 确实变了: {old_enabled} → {new_enabled}", changed,
              "后端状态没变，toggleRiskRule 的 apiPost 没生效！")
    else:
        check("规则名变了", False, "第一条规则名不一致")

# 4. 检查前端 HTML 结构（模拟 DOM 查询）
print(f"\n4. 检查前端 HTML 中 badge 是否能被 querySelector 找到")
import vnpy_webtrader, os
d = os.path.join(os.path.dirname(vnpy_webtrader.__file__), "static", "index.html")
with open(d, "r", encoding="utf-8") as f:
    html = f.read()

check("HTML 有 risk-status-badge class", "risk-status-badge" in html)
check("HTML 有 toggleRiskRule 函数", "toggleRiskRule" in html)
check("HTML 有 data-rule 属性（事件委托）", "data-rule=" in html)
check("HTML 有 getElementById badge 查找", "getElementById" in html and "badge_" in html)
check("HTML 有事件委托 addEventListener(change)", "addEventListener('change'" in html or 'addEventListener("change"' in html)

# 5. 检查事件委托代码
print(f"\n5. 检查事件委托 toggle 代码")
check("事件委托用 addEventListener('change')", "addEventListener('change'" in html or "addEventListener(\"change\"" in html)
check("通过 data-rule 读取规则名", "dataset.rule" in html or "data-rule" in html)
check("用 getElementById 找徽章", "getElementById" in html and "badge_" in html)
check("修改 badge.textContent", "textContent" in html)
check("修改 badge.className", "className" in html)

# 6. 检查 fallback 路径的 bug
print(f"\n6. 检查 loadRiskRules fallback bug")
fn_match2 = re.search(r'function loadRiskRules.*?\n\}', html, re.DOTALL)
if fn_match2:
    fn_body2 = fn_match2.group(0)
    fallback_sets_false = "typeof r==='string'?false:" in fn_body2 or 'typeof r=="string"?false:' in fn_body2
    if fallback_sets_false:
        check("fallback 路径 FORCES enabled=false（这是 BUG）", False,
              "当 /risk-rules 失败时 fallback 到 /risk-rule-names，但 names 接口没有 enabled 字段，所以全部变成已关闭！")
    else:
        check("fallback 路径处理正确", True)
else:
    check("找到 loadRiskRules 函数", False)

print(f"\n{'='*60}")
print(f"  结果: {PASS} 通过 / {FAIL} 失败")
if FAIL == 0:
    print("  全部通过")
else:
    print("  发现问题，请检查上述 FAIL 项")
print(f"{'='*60}")
