#  VeighNa 量化交易平台 — 妈妈版 v2.0

> 基于 [VeighNa](https://github.com/vnpy/vnpy) 构建的量化交易 Web 平台。浏览器即用，深色高级 UI。
> CTP 期货仿真 + 策略管理 + 算法交易 + 风控 + K 线图表 + 策略回测。

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0-blueviolet.svg"/>
  <img src="https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg"/>
  <img src="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
  <img src="https://img.shields.io/badge/license-MIT-orange.svg"/>
</p>

---

##  特性

- **浏览交易面板** — 9 个标签页，覆盖完整量化交易流程
-  **账户总览** — 总权益/可用资金/浮动盈亏/占用保证金，实时卡片
-  **持仓管理** — 合约/方向/持仓量/开仓价/当前价/盈亏，红绿标识
-  **一键下单** — 合约速查 + 买卖按钮 + 市价/限价 + 开平，确认弹窗
-  **委托记录** — 委托状态实时追踪
-  **CTA 策略管理** — 8 种内置策略，动态参数表单，一键启停
-  **算法交易** — TWAP/Iceberg/Sniper/BestLimit，自动拆单执行
-  **风控管理** — 5 条风控规则，开关控制 + 限值设置
-  **K 线图表** — 蜡烛图 + MA5/10/20/60 + 成交量 + 画线工具 + 缩放平移
-  **策略回测** — 双均线回测，权益曲线，收益率/回撤/胜率统计
-  **数据下载** — AKShare 免费下载 16 个期货品种 3 年日线数据
-  **纯模拟** — SimNow 仿真 2000 万 + PaperAccount 100 万，零风险练手

---

##  ️ 架构

```
浏览器 (http://127.0.0.1:8000)
    │  REST API + WebSocket
    ▼
run_web.py — FastAPI Web 服务 (端口 8000)
    │  RPC (tcp://127.0.0.1:2014/4102)
    ▼
run_server.py — VeighNa 交易引擎
    │  CTP + PaperAccount + CTA + Algo + Risk
```

---

##  快速开始

### 环境
- Python 3.10 ~ 3.13
- Windows / Ubuntu / macOS

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 下载历史数据（免费）
```bash
python download_data.py
```
16 个期货品种，每个约 725 条日线数据。

### 3. 配置 SimNow（可选）
编辑 `run_server.py`，填入 [SimNow](http://www.simnow.com.cn/) 账号：
```python
ctp_setting = {
    "用户名": "你的账号",
    "密码": "你的密码",
    ...
}
```

### 4. 启动
```bash
# 终端 1
python run_server.py

# 终端 2
python run_web.py
```

### 5. 打开
浏览器访问 **http://127.0.0.1:8000**  
默认登录：`admin` / `vnpy2024`

---

##  项目文件

| 文件 | 说明 |
|------|------|
| `run_server.py` | 交易引擎入口（CTP + RPC） |
| `run_web.py` | Web 服务入口（FastAPI） |
| `trading_dashboard.html` | 前端交易面板（单文件，9 标签） |
| `api_extended.py` | 扩展 API（策略/算法/风控/图表/回测） |
| `rpc_extensions.py` | RPC 客户端扩展 |
| `download_data.py` | AKShare 历史数据下载 |
| `fake_datafeed.py` | 假行情测试工具 |
| `test_all.py` | 33 项全功能测试 |
| `diagnose_ctp.py` | CTP 连接诊断 |
| `requirements.txt` | Python 依赖 |
| `data/` | 下载的历史数据（CSV） |

---

##  API 文档

启动后访问 http://127.0.0.1:8000/docs 查看 Swagger 文档。

新增量化 API（`/api/ext/`）：

| 分类 | 端点 |
|------|------|
| CTA 策略 | `GET /strategy-classes`, `POST /strategy/add|init|start|stop|remove` |
| 算法交易 | `GET /algo-templates`, `POST /algo/start|stop|pause|resume` |
| 风控管理 | `GET /risk-rules`, `POST /risk-rule/update|add` |
| K 线数据 | `GET /chart-list`, `GET /chart-data/{symbol}` |
| 策略回测 | `POST /backtest` |

---

##  测试

```bash
PYTHONIOENCODING=utf-8 python test_all.py
```
33 项测试覆盖：服务器状态、认证、基础交易 API、策略管理、算法交易、风控管理、前端页面。

---

##  已知限制

- **CTP 需交易时段**（9:00-11:30, 13:30-15:00, 21:00+），非交易时段账户/行情数据为空
- **CTA 策略引擎**需 CTP 连接后才能产生真实信号
- **TuShare 新账号**需积分才能调用数据接口（AKShare 替代）

---

##  许可

MIT License

##  致谢

- [VeighNa](https://github.com/vnpy/vnpy) — 开源量化交易框架
- [SimNow](http://www.simnow.com.cn/) — 期货仿真平台
- [AKShare](https://github.com/akfamily/akshare) — 免费开源金融数据
- [Plotly.js](https://plotly.com/javascript/) — 交互式图表库
