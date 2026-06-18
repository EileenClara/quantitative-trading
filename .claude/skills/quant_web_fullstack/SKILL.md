# Quant WebTrader Fullstack Development Rule (AUTO-TRIGGER)

## Trigger
When the user requests ANY of: trading panel, account overview, positions, order form, order history, vnpy, WebTrader, FastAPI, SimNow, futures frontend, trading dashboard, trading UI.

## CRITICAL: Output Standard

### 1. Frontend MUST include real data interaction
- ALL monetary values (total equity, available, margin, P&L) fetched from `/api/account` via REST, NEVER hardcoded
- ALL position tables fetched from `/api/position`, with real-time refresh via WebSocket
- Order form binds to `POST /api/order` with loading state, error toast, and order receipt callback
- WebSocket connection to `ws://127.0.0.1:8000/ws/?token=xxx` for real-time tick/account/position push
- Handle edge cases: connection lost → reconnect, API timeout → error state, empty data → empty state UI
- Auth: JWT token from `POST /token`, attach `Authorization: Bearer <token>` to all requests

### 2. MUST include backend API code snippets alongside frontend
For every frontend feature, also output the corresponding backend endpoint:
```
Frontend: fetchAccount() → GET /api/account
Backend:  @app.get("/api/account") → rpc_client.get_all_accounts() → RpcServer → MainEngine → CTP
```

Data flow annotation required:
```
Browser UI → REST/WebSocket → FastAPI(process 2, port 8000) → RpcClient → RpcServer(process 1, port 2014/4102) → MainEngine + CTP(SimNow)
```

### 3. API endpoints reference
| Frontend Need | API Call |
|---|---|
| Account overview cards | `GET /account` → `{balance, available, margin, ...}` |
| Positions table | `GET /position` → `[{symbol, direction, volume, price, pnl}, ...]` |
| Place order | `POST /order` → `{symbol, exchange, direction, offset, price, volume}` |
| Cancel order | `DELETE /order/{vt_orderid}` |
| Order history | `GET /order` → `[{status, symbol, direction, price, volume, time}, ...]` |
| Trade history | `GET /trade` |
| Real-time push | `WS /ws/?token=xxx` → `{topic, data}` |
| Contracts | `GET /contract` → datalist for input autocomplete |
| Strategy classes | `GET /api/ext/strategy-classes` |
| Add strategy | `POST /api/ext/strategy/add` |
| Running strategies | `GET /api/ext/strategies` |
| Algo templates | `GET /api/ext/algo-templates` |
| Start algo | `POST /api/ext/algo/start` |
| Risk rules | `GET /api/ext/risk-rules` |
| Toggle risk rule | `POST /api/ext/risk-rule/update` |

## FORBIDDEN
1. DO NOT hardcode fake numbers (100万, 71500 price, +2500 profit)
2. DO NOT write pure static HTML without fetch()/WebSocket calls
3. DO NOT create UI without corresponding backend API code
4. DO NOT ignore error/empty/reconnect states
5. DO NOT skip the data flow annotation

## When you see demo/fallback data
If the API returns empty (no broker connected), you MAY show demo data BUT MUST:
- Clearly label it as "示例数据"
- Still include real API calls that WILL work when broker connects
- Show the API connection status indicator

## AFTER EVERY CODE CHANGE
Run the test suite:
```bash
PYTHONIOENCODING=utf-8 python test_all.py
```
All 33 tests must pass before considering the change complete. If any fail, fix them before moving on.
