import math

from vnpy.app.position_manager import StrategyTemplate
from vnpy.trader.utility import BarGenerator

from vnpy.trader.tqz_extern.tools.position_operator.position_operator import TQZPositionJsonOperator
from vnpy.trader.tqz_extern.tools.file_path_operator.file_path_operator import TQZFilePathOperator
from vnpy.trader.tqz_extern.tools.position_data.position_data import TQZPositionData
from vnpy.trader.tqz_extern.tools.symbol_operator.symbol_operator import (
    TQZSymbolOperator,
    TQZFuturesType
)

from vnpy.trader.constant import Direction
from vnpy.trader.object import (
    TickData
)

from vnpy.app.position_manager.tqz_constant import (
    TQZSynchronizeTimesKey,
    TQZOrderSendType
)

class TQZSynchronizePositions(StrategyTemplate):

    author = "Post-Truth"

    # 策略参数
    synchronize_times = 10
    offset_tick_counts = 5

    parameters = ["offset_tick_counts", "synchronize_times"]
    variables = []

    def __init__(self, strategy_engine, strategy_name, vt_symbols, setting):
        """  """
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        print("TQZSynchronizePositions init")

        self.bar_generators: {str: BarGenerator} = {}
        self.vt_symbols_limit_prices: {str: TickData} = {}
        self.vt_symbols_synchronize_times = {}

        self.last_time_slot = 0
        self.last_minute = -1

        self.vt_symbols = self.tqz_update_vt_symbols()
        print("cta_strategy_data: " + str(self.current_strategy_data))
        print("self.vt_symbols: " + str(self.vt_symbols))

        for vt_symbol in self.vt_symbols:
            self.bar_generators[vt_symbol] = BarGenerator(on_bar=self.on_bar)


    def on_init(self):
        """
        Callback when strategy is inited.
        """
        
        print("TQZSynchronizePositions on_init")
        self.write_log("策略初始化")


    def on_start(self):
        """
        Callback when strategy is started.
        """
        print("TQZSynchronizePositions on_start")
        self.write_log("策略启动")


    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        print("on_stop")
        self.write_log("策略停止")


    def on_tick(self, tick):
        """
        Callback of new tick data update.
        """
        self.vt_symbols_limit_prices[tick.vt_symbol] = tick

        self.on_x_seconds(tick=tick, seconds_interval=20)


    def on_x_seconds(self, tick: TickData, seconds_interval):
        """
        Callback of per interval seconds is gone.
        """
        if self.__is_new_time_slot(tick=tick, seconds_interval=seconds_interval) is False:
            return

        self.cancel_all()
        print("tick.vt_symbol: " + str(tick.vt_symbol), end="  ")
        print("datatime: " + str(tick.datetime))

        strategy_position_buy, strategy_position_sell, real_position_buy, real_position_sell = self.tqz_get_strategy_position_and_real_position(
            market_vt_symbol=tick.vt_symbol,
            strategy_data=self.current_strategy_data
        )
        current_futures_type = TQZSymbolOperator.tqz_get_futures_type(vt_symbol=tick.vt_symbol)
        min_offset_price = self.strategy_engine.contracts[tick.vt_symbol].pricetick

        # do nothing when current symbol is in syncronized condition
        if self.__tqz_strategy_is_real(
                strategy_position_buy=strategy_position_buy,
                strategy_position_sell=strategy_position_sell,
                real_position_buy=real_position_buy,
                real_position_sell=real_position_sell,
                futures_type=current_futures_type
        ) is True:
            return

        if (tick.vt_symbol not in self.current_strategy_data.keys()) or current_futures_type in [TQZFuturesType.COMMODITY_FUTURES, TQZFuturesType.TREASURY_FUTURES]:

            self.tqz_synchronization_position_min_netting_mode(
                market_vt_symbol=tick.vt_symbol,
                now_price=tick.last_price,
                offset_price=(min_offset_price * self.offset_tick_counts),
                strategy_position_buy=strategy_position_buy,
                strategy_position_sell=strategy_position_sell,
                real_position_buy=real_position_buy,
                real_position_sell=real_position_sell
            )

        elif current_futures_type is TQZFuturesType.STOCK_INDEX_FUTURES:

            self.tqz_synchronization_position_cffex_lock_mode(
                market_vt_symbol=tick.vt_symbol,
                now_price=tick.last_price,
                offset_price=(min_offset_price * self.offset_tick_counts),
                strategy_position_net=(strategy_position_buy - strategy_position_sell),
                real_position_net=(real_position_buy - real_position_sell)
            )

        else:
            self.write_log("futures_type: " + str(current_futures_type) + " is out of futures type")

        self.put_event()


    # --- send order part ---
    def tqz_synchronization_position_cffex_lock_mode(self, market_vt_symbol, now_price, offset_price, strategy_position_net, real_position_net):
        """
        synchronization position with lock mode(cffex mode)
        """

        vt_orderids = []
        buy_price = min(now_price + offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_up)
        sell_price = max(now_price - offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_down)

        if strategy_position_net >= 0 and real_position_net >= 0:

            if strategy_position_net > real_position_net:
                vt_orderids = self.tqz_buy(
                    vt_symbol=market_vt_symbol,
                    price=buy_price,
                    lots=TQZPositionData.tqz_risk_control(lot=strategy_position_net-real_position_net),
                    lock=True
                )
            elif strategy_position_net < real_position_net:
                vt_orderids = self.tqz_sell(
                    vt_symbol=market_vt_symbol,
                    price=sell_price,
                    lots=TQZPositionData.tqz_risk_control(lot=real_position_net - strategy_position_net),
                    lock=True
                )
            elif strategy_position_net is real_position_net:
                pass

        elif strategy_position_net >= 0 and real_position_net <= 0:

            vt_orderids = self.tqz_buy(
                vt_symbol=market_vt_symbol,
                price=buy_price,
                lots=TQZPositionData.tqz_risk_control(lot=strategy_position_net-real_position_net),
                lock=True
            )

        elif strategy_position_net <= 0 and real_position_net >= 0:

            vt_orderids = self.tqz_short(
                vt_symbol=market_vt_symbol,
                price=sell_price,
                lots=TQZPositionData.tqz_risk_control(lot=real_position_net - strategy_position_net),
                lock=True
            )

        elif strategy_position_net <= 0 and real_position_net <= 0:

            if abs(strategy_position_net) > abs(real_position_net):
                vt_orderids = self.tqz_short(
                    vt_symbol=market_vt_symbol,
                    price=sell_price,
                    lots=TQZPositionData.tqz_risk_control(lot=abs(strategy_position_net)-abs(real_position_net)),
                    lock=True
                )
            elif abs(strategy_position_net) < abs(real_position_net):
                vt_orderids = self.tqz_cover(
                    vt_symbol=market_vt_symbol,
                    price=buy_price,
                    lots=TQZPositionData.tqz_risk_control(lot=abs(real_position_net) - abs(strategy_position_net)),
                    lock=True
                )
            elif strategy_position_net is real_position_net:
                pass

        return vt_orderids


    def tqz_synchronization_position_min_netting_mode(self, market_vt_symbol, now_price, offset_price, strategy_position_buy, strategy_position_sell, real_position_buy, real_position_sell):
        """
        synchronization position in min netting with double direction(buy direction & sell direction) mode.
        """

        buy_vt_orderids = []
        sell_vt_orderids = []

        buy_price = min(now_price + offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_up)
        sell_price = max(now_price - offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_down)

        net_buy_lots_abs = abs(strategy_position_buy - real_position_buy)
        net_sell_lots_abs = abs(strategy_position_sell - real_position_sell)


        if net_buy_lots_abs >= net_sell_lots_abs:

            if strategy_position_buy < real_position_buy:
                sell_vt_orderids = self.tqz_sell(
                    vt_symbol=market_vt_symbol,
                    price=sell_price,
                    lots=TQZPositionData.tqz_risk_control(lot=net_buy_lots_abs)
                )
            elif strategy_position_buy > real_position_buy:
                buy_vt_orderids = self.tqz_buy(
                    vt_symbol=market_vt_symbol,
                    price=buy_price,
                    lots=TQZPositionData.tqz_risk_control(lot=net_buy_lots_abs)
                )
            else:
                pass

        else:

            if strategy_position_sell > real_position_sell:
                sell_vt_orderids = self.tqz_short(
                    vt_symbol=market_vt_symbol,
                    price=sell_price,
                    lots=TQZPositionData.tqz_risk_control(lot=net_sell_lots_abs)
                )
            elif strategy_position_sell < real_position_sell:
                buy_vt_orderids = self.tqz_cover(
                    vt_symbol=market_vt_symbol,
                    price=buy_price,
                    lots=TQZPositionData.tqz_risk_control(lot=net_sell_lots_abs)
                )
            else:
                pass

        return list(set(buy_vt_orderids + sell_vt_orderids))


    # --- strategy & real data part ---
    def tqz_update_vt_symbols(self):
        """
        Update and Merge current strategy vt_symbols and real vt_symbols, return a new vt_symbols list(strategy and real)
        """

        real_vt_symbols = []
        [real_vt_symbols.append(
            TQZSymbolOperator.get_vt_symbol(
                strategy_symbol=position_data_model.vt_symbol_direction
            )
        ) for position_data_model in TQZPositionData.position_data_models()]

        strategy_vt_symbols = list(set(TQZSymbolOperator.tqz_get_strategy_vt_symbols(
            self.current_strategy_data.keys()
        )))

        return list(set(strategy_vt_symbols + real_vt_symbols))

    @property
    def current_strategy_data(self):
        """ """

        single_strategy_path = TQZFilePathOperator.current_file_grandfather_path(
            file=TQZFilePathOperator.grandfather_path(
                source_path=TQZFilePathOperator.father_path(source_path=__file__)
            )
        ) + '/.vntrader/position_manager_data.json'

        single_strategy_content = TQZPositionJsonOperator.tqz_get_sum_position_format_data(single_strategy_path)
        cta_strategy_data = TQZPositionJsonOperator.tqz_get_sum_position_format_data_with_jsonfileContentList(
            single_strategy_content
        )

        # cta_strategy_data = TQZPositionJsonOperator.tqz_load_jsonfile(jsonfile=single_strategy_path)

        return cta_strategy_data

    def tqz_get_strategy_position_and_real_position(self, market_vt_symbol, strategy_data):
        """
        get real position(buy, sell) and strategy position(buy, sell)
        """

        # strategy position
        strategy_position_buy = TQZSymbolOperator.tqz_get_strategy_position(
            market_vt_symbol=market_vt_symbol,
            direction=Direction.LONG,
            strategy_data=strategy_data
        )
        strategy_position_sell = TQZSymbolOperator.tqz_get_strategy_position(
            market_vt_symbol=market_vt_symbol,
            direction=Direction.SHORT,
            strategy_data=strategy_data
        )

        # real position
        real_position_buy = self.tqz_get_real_position(
            market_vt_symbol=market_vt_symbol,
            direction=Direction.LONG
        )
        real_position_sell = self.tqz_get_real_position(
            market_vt_symbol=market_vt_symbol,
            direction=Direction.SHORT
        )

        return strategy_position_buy, strategy_position_sell, real_position_buy, real_position_sell


    # --- over write send order part ---
    def tqz_buy(self, vt_symbol, price, lots, lock=False):
        """
        Over write method of send buy order.
        """

        if lots is 0:
            return []
        else:
            unit_lots = self.__get_unit_lots(vt_symbol=vt_symbol, lots=lots, order_send_type=TQZOrderSendType.BUY)
            buy_result = self.buy(vt_symbol=vt_symbol, price=price, volume=unit_lots, lock=lock)

            print(f'{vt_symbol}  拆单前开多: {lots} 手,  拆单后开多: {unit_lots} 手', end="  ")
            print(f'buy_result: {buy_result}')

            return buy_result

    def tqz_sell(self, vt_symbol, price, lots, lock=False):
        """
        Over write method of send sell order.
        """

        if lots is 0:
            return []
        else:
            unit_lots = self.__get_unit_lots(vt_symbol=vt_symbol, lots=lots, order_send_type=TQZOrderSendType.SELL)
            sell_result = self.sell(vt_symbol=vt_symbol, price=price, volume=unit_lots, lock=lock)

            print(f'{vt_symbol}  拆单前平多: {lots} 手,  拆单后平多: {unit_lots} 手', end="  ")
            print("sell_result: " + str(sell_result))

            return sell_result

    def tqz_short(self, vt_symbol, price, lots, lock=False):
        """
        Over write method of send short order.
        """

        if lots is 0:
            return []
        else:
            unit_lots = self.__get_unit_lots(vt_symbol=vt_symbol, lots=lots, order_send_type=TQZOrderSendType.SHORT)
            short_result = self.short(vt_symbol=vt_symbol, price=price, volume=unit_lots, lock=lock)

            print(f'{vt_symbol}  拆单前开空: {lots} 手,  拆单后开空: {unit_lots} 手', end="  ")
            print("short_result: " + str(short_result))

            return short_result

    def tqz_cover(self, vt_symbol, price, lots, lock=False):
        """
        Over write method of send cover order.
        """

        if lots is 0:
            return []
        else:
            unit_lots = self.__get_unit_lots(vt_symbol=vt_symbol, lots=lots, order_send_type=TQZOrderSendType.COVER)
            cover_result = self.cover(vt_symbol=vt_symbol, price=price, volume=unit_lots, lock=lock)

            print(f'{vt_symbol}  拆单前平空: {lots} 手,  拆单后平空: {unit_lots} 手', end="  ")
            print("cover_result: " + str(cover_result))

            return cover_result



    # ------ private part ------
    def __tqz_strategy_is_real(self, strategy_position_buy, real_position_buy, strategy_position_sell, real_position_sell, futures_type: TQZFuturesType):
        """
        strategy position(buy, sell) is real position(buy, sell) or not
        """

        if futures_type in [TQZFuturesType.COMMODITY_FUTURES, TQZFuturesType.TREASURY_FUTURES]:
            is_same = (strategy_position_buy is real_position_buy) and (strategy_position_sell is real_position_sell)
        elif futures_type is TQZFuturesType.STOCK_INDEX_FUTURES:
            is_same = (strategy_position_buy - strategy_position_sell) is (real_position_buy - real_position_sell)
        else:
            self.write_log("__tqz_strategy_is_real: futures_type is error.")
            is_same = True

        return is_same


    def __update_synchronize_times(self, vt_symbol, order_send_type: TQZOrderSendType):
        """
        Update synchronize times when send new order.
        """
        
        default_step = 1
        default_synchronize_times = 0
        
        # add new vt_symbol to self.vt_symbols_synchronize_times
        if vt_symbol not in self.vt_symbols_synchronize_times.keys():
            self.vt_symbols_synchronize_times[vt_symbol] = {}
            self.vt_symbols_synchronize_times[vt_symbol][TQZSynchronizeTimesKey.BUY_SYNCHRONIZE_TIMES.value] = default_synchronize_times
            self.vt_symbols_synchronize_times[vt_symbol][TQZSynchronizeTimesKey.SELL_SYNCHRONIZE_TIMES.value] = default_synchronize_times
            self.vt_symbols_synchronize_times[vt_symbol][TQZSynchronizeTimesKey.SHORT_SYNCHRONIZE_TIMES.value] = default_synchronize_times
            self.vt_symbols_synchronize_times[vt_symbol][TQZSynchronizeTimesKey.COVER_SYNCHRONIZE_TIMES.value] = default_synchronize_times
        
        # update synchronize times with order_send_type
        if order_send_type in [
            TQZOrderSendType.BUY, 
            TQZOrderSendType.SELL, 
            TQZOrderSendType.SHORT,
            TQZOrderSendType.COVER
        ]:
            if self.vt_symbols_synchronize_times[vt_symbol][order_send_type.value] < self.__get_max_signal_direction_synchronize_times(
                synchronize_times=self.synchronize_times
            ):
                self.vt_symbols_synchronize_times[vt_symbol][order_send_type.value] += default_step


    @staticmethod
    def __get_max_signal_direction_synchronize_times(synchronize_times):
        """
        Get synchronize times of max signal direction
        """

        if synchronize_times < 0:
            return 0

        signal_direction_synchronize_times = math.floor(synchronize_times / 2)

        if signal_direction_synchronize_times is 0:
            signal_direction_synchronize_times = 1

        return signal_direction_synchronize_times


    def __get_unit_lots(self, vt_symbol, lots, order_send_type: TQZOrderSendType):
        """
        Get unit_lots with vt_symbol lots and order_send_type.
        """

        self.__update_synchronize_times(
            vt_symbol=vt_symbol,
            order_send_type=TQZOrderSendType.BUY
        )

        max_signal_direction_synchronize_times = self.__get_max_signal_direction_synchronize_times(
            synchronize_times=self.synchronize_times
        )
        leftover_synchronize_times = max_signal_direction_synchronize_times - self.vt_symbols_synchronize_times[vt_symbol][order_send_type.value] + 1

        # send 1 lot at least.
        unit_lots = math.floor(lots / leftover_synchronize_times)
        if unit_lots is 0:
            unit_lots = 1

        # last synchronize time.
        if self.vt_symbols_synchronize_times[vt_symbol][order_send_type.value] is max_signal_direction_synchronize_times:
            unit_lots = lots

        return unit_lots

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