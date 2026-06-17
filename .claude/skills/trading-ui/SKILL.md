# Trading Dashboard UI Skill

You are designing a web-based trading dashboard for VeighNa quantitative trading platform.

## Target User
A non-technical mother who understands futures trading terminology but not programming.
She needs: simple layout, big fonts, clear buttons, safety confirmations.

## Design System

### Colors
- Background: #0f1923 (deep navy)
- Cards: #1a2740
- Accent: #c9a96e (warm gold)
- Text: #f0efe7 (warm white)
- Profit green: #3a7d5c
- Loss red: #c0392b
- Quant blue: #5dade2 (for strategy/algo tabs)
- Muted: #8899aa, #667788, #445566

### Typography
- Chinese: Microsoft YaHei, PingFang SC
- System sans-serif stack
- Numbers: large, bold, monospaced feel
- Labels: 12-13px uppercase style
- Values: 28-32px bold

### Components
- Cards: rounded-14px, subtle border rgba(255,255,255,0.04), hover lift effect
- Buttons: rounded-8px/10px, gradient gold for primary, color-tinted for actions
- Tables: clean, minimal borders, hover highlight
- Badges: colored backgrounds at 20% opacity, 12px font
- Modals: centered, backdrop blur, gold accent border
- Tabs: horizontal pill navigation

### Layout
- Sticky top bar with title + total equity
- Horizontal tab navigation below
- Main content area with max-width 1500px
- Sticky bottom status bar
- Desktop-first, responsive as secondary concern

### Safety Rules
- ALL trading actions require confirmation modal
- Modal shows plain-language summary: "您即将买入 5 手 cu2506，价格：市价，开仓"
- Demo mode clearly indicated with yellow banner
- Status bar in human language, not engineering terms

### JS API Pattern
- Auth: JWT token from POST /token
- All API calls use Bearer token
- REST: apiGet(path), apiPost(path, body)
- WebSocket: ws://127.0.0.1:8000/ws/?token=xxx
- Fallback to demo data when API returns empty (for visual testing)
- Refresh every 10 seconds

### Tabs
1. 账户总览 - account overview with stat cards
2. 持仓管理 - positions table
3. 下单交易 - order form with contract reference
4. 委托记录 - order history table
5. CTA 策略 - strategy management (quant blue accent)
6. 算法交易 - algo trading (quant blue accent)
7. 风控管理 - risk management (quant blue accent)
