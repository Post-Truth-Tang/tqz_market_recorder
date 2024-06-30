from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)

from vnpy.trader.constant import Status, Direction

import math


class AtrRsiStrategyTestLog(CtaTemplate):
    """"""

    author = "Post-Truth"

    atr_length = 22
    atr_ma_length = 10
    rsi_length = 5
    rsi_entry = 16
    trailing_percent = 0.8
    fixed_size = 5

    atr_value = 0
    atr_ma = 0
    rsi_value = 0
    rsi_buy = 0
    rsi_sell = 0
    intra_trade_high = 0
    intra_trade_low = 0

    parameters = [
        "atr_length",
        "atr_ma_length",
        "rsi_length",
        "rsi_entry",
        "trailing_percent",
        "fixed_size"
    ]
    variables = [
        "atr_value",
        "atr_ma",
        "rsi_value",
        "rsi_buy",
        "rsi_sell",
        "intra_trade_high",
        "intra_trade_low"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()

        self.last_time_slot = 0
        self.last_minute = -1

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")


    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")


    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")


    def on_tick(self, tick: TickData):
        """
        Callback when new tick data update.
        """

        self.on_x_seconds(tick=tick)


    def on_x_seconds(self, tick: TickData, seconds_interval: int = 5):
        """
        Callback when x seconds pass or new minute coming.
        """
        if self.__is_new_time_slot(tick=tick, seconds_interval=seconds_interval) is False:
            return

        self.cancel_all()

        if self.pos is 0:
            self.tqz_buy(price=tick.last_price + 5, lots=self.fixed_size)
        elif 0 < self.pos < self.fixed_size:
            self.tqz_buy(price=tick.last_price + 5, lots=(self.fixed_size - self.pos))
        elif self.pos is self.fixed_size:
            self.tqz_sell(price=tick.last_price - 5, lots=abs(self.pos))
        elif self.pos is (self.fixed_size * -1):
            short_stop = self.intra_trade_low * (1 + self.trailing_percent / 100)
            self.tqz_cover(price=short_stop, lots=abs(self.pos), stop=True)
        elif 0 > self.pos > self.fixed_size:
            short_stop = self.intra_trade_low * (1 + self.trailing_percent / 100)
            self.tqz_short(price=short_stop, lots=abs(self.fixed_size - self.pos), stop=True)

        self.put_event()


    def __is_new_time_slot(self, tick: TickData, seconds_interval):
        """
        Judge current time_slot is new or not.
        """

        current_time_slot = math.floor(tick.datetime.second / seconds_interval)

        if tick.datetime.minute != self.last_minute:  # new minute is come
            self.last_time_slot, self.last_minute, is_new = current_time_slot, tick.datetime.minute, True
        elif current_time_slot != self.last_time_slot:  # new minute is not come, but last_time_slot is update
            self.last_time_slot, self.last_minute, is_new = current_time_slot, tick.datetime.minute, True
        else:
            is_new = False

        return is_new


    def tqz_buy(self, price, lots, stop: bool = False, lock: bool = False):
        """
        Re write send buy order.
        """

        print("[strategy tqz_buy]", end="  ")
        print("before self.pos: " + str(self.pos), end="  ")

        self.pos += lots
        self.buy(price=price, volume=lots, stop=stop, lock=lock)
        self.sync_data()

        print("after self.pos: " + str(self.pos))


    def tqz_sell(self, price, lots, stop: bool = False, lock: bool = False):
        """
        Re write send sell order.
        """

        print("[strategy tqz_sell]", end="  ")
        print("before self.pos: " + str(self.pos), end="  ")

        self.pos -= lots
        self.sell(price=price, volume=lots, stop=stop, lock=lock)
        self.sync_data()

        print("after self.pos: " + str(self.pos))


    def tqz_short(self, price, lots, stop: bool = False, lock: bool = False):
        """
        Re write send short order.
        """

        print("[strategy tqz_short]", end="  ")
        print("before self.pos: " + str(self.pos), end="  ")

        self.pos -= lots
        self.short(price=price, volume=lots, stop=stop, lock=lock)
        self.sync_data()

        print("after self.pos: " + str(self.pos))


    def tqz_cover(self, price, lots, stop: bool = False, lock: bool = False):
        """
        Re write send cover order.
        """

        print("[strategy tqz_cover]", end="  ")
        print("before self.pos: " + str(self.pos), end="  ")

        self.pos += lots
        self.cover(price=price, volume=lots, stop=stop, lock=lock)
        self.sync_data()

        print("after self.pos: " + str(self.pos))


    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """

        if order.status in [Status.CANCELLED, Status.REJECTED]:

            if order.direction in [Direction.LONG]:
                self.pos -= order.volume
            elif order.direction in [Direction.SHORT]:
                self.pos += order.volume

        if order.status in [Status.CANCELLED, Status.REJECTED, Status.ALLTRADED]:
            self.sync_data()


    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """

        pass


    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass
