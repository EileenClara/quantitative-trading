"""
模拟行情数据源 —— 生成随机 tick 数据用于测试
当 CTP 连不上时，用这个让策略能动起来
"""
import random
import time
import threading
from datetime import datetime
from vnpy.trader.object import TickData, ContractData
from vnpy.trader.constant import Exchange, Product
from vnpy.trader.event import EVENT_TICK, EVENT_CONTRACT
from vnpy.event import Event


class FakeDataFeed:
    """假行情源，生成随机价格波动"""

    def __init__(self, event_engine):
        self.event_engine = event_engine
        self.active = False
        self.thread = None
        self.prices = {}  # vt_symbol -> current_price

    def start(self, symbols=None):
        """启动假行情推送"""
        if symbols is None:
            symbols = [
                "cu2506.SHFE", "rb2510.SHFE", "i2509.DCE",
                "sc2509.INE", "m2509.DCE", "MA509.ZCE",
            ]
        # 先推送合约数据（让策略可以订阅）
        for sym in symbols:
            contract = self._make_contract(sym)
            self.event_engine.put(Event(EVENT_CONTRACT, contract))

        for sym in symbols:
            base_prices = {
                "cu2506.SHFE": 71500, "rb2510.SHFE": 4200,
                "i2509.DCE": 850, "sc2509.INE": 520,
                "m2509.DCE": 3150, "MA509.ZCE": 2450,
            }
            self.prices[sym] = base_prices.get(sym, 1000)

        self.active = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"[FakeDataFeed] 推送 {len(symbols)} 个合约的模拟行情 + 合约数据")

    def _make_contract(self, vt_symbol):
        symbol, exchange_str = vt_symbol.split(".")
        exchange = Exchange.__members__.get(exchange_str, Exchange.SHFE)
        c = ContractData(
            symbol=symbol,
            exchange=exchange,
            name=symbol,
            product=Product.FUTURES,
            size=10,
            pricetick=1,
            gateway_name="FAKE",
        )
        c.vt_symbol = vt_symbol
        return c

    def stop(self):
        self.active = False

    def _run(self):
        while self.active:
            for vt_symbol, price in list(self.prices.items()):
                tick = self._generate_tick(vt_symbol, price)
                self.event_engine.put(Event(EVENT_TICK, tick))
            time.sleep(1)  # 每秒推一次

    def _generate_tick(self, vt_symbol, last_price):
        symbol, exchange_str = vt_symbol.split(".")
        exchange = Exchange.__members__.get(exchange_str, Exchange.SHFE)

        change = random.uniform(-last_price * 0.001, last_price * 0.001)
        new_price = round(last_price + change, 2)
        self.prices[vt_symbol] = new_price

        bid = round(new_price - random.uniform(1, 5), 2)
        ask = round(new_price + random.uniform(1, 5), 2)

        tick = TickData(
            symbol=symbol,
            exchange=exchange,
            datetime=datetime.now(),
            gateway_name="FAKE",
            name=symbol,
            volume=random.randint(100, 1000),
            turnover=random.randint(1000000, 10000000),
            open_price=last_price,
            high_price=ask,
            low_price=bid,
            pre_close=last_price,
            last_price=new_price,
            bid_price_1=bid,
            bid_volume_1=random.randint(1, 50),
            ask_price_1=ask,
            ask_volume_1=random.randint(1, 50),
        )
        tick.vt_symbol = vt_symbol
        return tick
