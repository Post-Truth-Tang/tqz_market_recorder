from vnpy.app.position_manager import StrategyTemplate
from vnpy.trader.utility import BarGenerator
from typing import List

from vnpy.trader.tqz_extern.tools.position_operator.position_operator import TQZPositionJsonOperator
from vnpy.trader.tqz_extern.tools.file_path_operator.file_path_operator import TQZFilePathOperator
from vnpy.trader.tqz_extern.tools.symbol_operator.symbol_operator import (TQZSymbolOperator, TQZFuturesType)
from vnpy.trader.tqz_extern.tools.position_data.position_data import TQZPositionData

from vnpy.app.position_manager.tqz_constant import TQZSynchronizeSettingType

from vnpy.trader.object import (
    TickData,
    BarData,
    OrderData,
    TradeData,
    StopOrder
)
from vnpy.trader.constant import (
    Direction,
    Product
)


class PositionManager(StrategyTemplate):

    author = "Post-Truth"

    # 策略参数
    offset_tick_counts = 5
    parameters = ["offset_tick_counts"]
    variables = []

    def __init__(self, strategy_engine, strategy_name, vt_symbols, setting):
        """  """
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        print("PositionManager init")

        self.bar_generators: {str: BarGenerator} = {}
        self.vt_symbols_limit_prices: {str: TickData} = {}

        self.vt_symbols = TQZSymbolOperator.tqz_get_strategy_vt_symbols(self.current_strategy_data.keys())
        print("self.vt_symbols: " + str(self.vt_symbols))
        print("self.current_strategy_data: " + str(self.current_strategy_data))

        for vt_symbol in self.vt_symbols:
            self.bar_generators[vt_symbol] = BarGenerator(on_bar=self.on_bar)

    def on_init(self):
        """
        Callback when strategy is inited.
        """

        print("PositionManager on_init")
        self.write_log("策略初始化")

    def on_start(self):
        """
        Callback when strategy is started.
        """

        print("PositionManager on_start")
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        print("on_stop")
        self.write_log("策略停止")

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        pass

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass

    def on_tick(self, tick):
        """
        Callback of new tick data update.
        """

        self.vt_symbols_limit_prices[tick.vt_symbol] = tick
        self.bar_generators[tick.vt_symbol].update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.cancel_all()
        print("bar.vt_symbol: " + str(bar.vt_symbol), end="  ")
        print("datatime: " + str(bar.datetime))

        strategy_position_buy, strategy_position_sell, real_position_buy, real_position_sell = self.tqz_get_strategy_position_and_real_position(
            market_vt_symbol=bar.vt_symbol,
            strategy_data=self.current_strategy_data
        )

        current_futures_type = TQZSymbolOperator.tqz_get_futures_type(vt_symbol=bar.vt_symbol)
        current_strategy_vt_symbols = TQZSymbolOperator.tqz_get_strategy_vt_symbols(
            self.current_strategy_data.keys()
        )
        min_offset_price = self.strategy_engine.contracts[bar.vt_symbol].pricetick

        # do nothing when current symbol is in syncronized condition
        if self.__tqz_strategy_is_real(
            strategy_position_buy=strategy_position_buy,
            strategy_position_sell=strategy_position_sell,
            real_position_buy=real_position_buy,
            real_position_sell=real_position_sell,
            futures_type=current_futures_type
        ) is True:
            return

        if (bar.vt_symbol not in current_strategy_vt_symbols) or current_futures_type in [
            TQZFuturesType.COMMODITY_FUTURES,
            TQZFuturesType.TREASURY_FUTURES
        ]:
            self.tqz_synchronization_position_double_direction_mode(
                market_vt_symbol=bar.vt_symbol,
                now_price=bar.close_price,
                offset_price=(min_offset_price * self.offset_tick_counts),
                strategy_position_buy=strategy_position_buy,
                strategy_position_sell=strategy_position_sell,
                real_position_buy=real_position_buy,
                real_position_sell=real_position_sell
            )

        elif current_futures_type is TQZFuturesType.STOCK_INDEX_FUTURES:
            self.tqz_synchronization_position_cffex_lock_mode(
                market_vt_symbol=bar.vt_symbol,
                now_price=bar.close_price,
                offset_price=(min_offset_price * self.offset_tick_counts),
                strategy_position_net=(strategy_position_buy - strategy_position_sell),
                real_position_net=(real_position_buy - real_position_sell)
            )

        else:
            self.write_log("futures_type: " + str(current_futures_type) + " is out of futures type")

        self.put_event()


    def tqz_synchronization_position_cffex_lock_mode(self, market_vt_symbol, now_price, offset_price, strategy_position_net, real_position_net):
        """
        synchronization position with lock mode(cffex mode)
        """

        vt_orderids = []
        buy_price = min(now_price + offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_up)
        sell_price = max(now_price - offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_down)

        if strategy_position_net >= 0 and real_position_net >= 0:

            if strategy_position_net > real_position_net:

                lot = TQZPositionData.tqz_risk_control(lot=strategy_position_net-real_position_net)
                print(f'开多 {str(lot)} 手', end="  ")
                vt_orderids = self.buy(vt_symbol=market_vt_symbol, price=buy_price, volume=lot, lock=True)
                print(f'vt_orderids: {vt_orderids}')

            elif strategy_position_net < real_position_net:

                lot = TQZPositionData.tqz_risk_control(lot=real_position_net - strategy_position_net)
                print(f'平多 {str(lot)} 手', end="  ")
                vt_orderids = self.sell(vt_symbol=market_vt_symbol, price=sell_price, volume=lot, lock=True)
                print(f'vt_orderids: {vt_orderids}')

            elif strategy_position_net is real_position_net:
                print(f'净仓相等, 不做处理')

        elif strategy_position_net >= 0 and real_position_net <= 0:

            lot = TQZPositionData.tqz_risk_control(lot=strategy_position_net-real_position_net)
            print(f'开多 {str(lot)} 手', end="  ")
            vt_orderids = self.buy(vt_symbol=market_vt_symbol, price=buy_price, volume=lot, lock=True)
            print(f'vt_orderids: {vt_orderids}')

        elif strategy_position_net <= 0 and real_position_net >= 0:

            lot = TQZPositionData.tqz_risk_control(lot=real_position_net - strategy_position_net)
            print(f'开空 {str(lot)} 手', end="  ")
            vt_orderids = self.short(vt_symbol=market_vt_symbol, price=sell_price, volume=lot, lock=True)
            print(f'vt_orderids: {vt_orderids}')

        elif strategy_position_net <= 0 and real_position_net <= 0:

            if abs(strategy_position_net) > abs(real_position_net):

                lot = TQZPositionData.tqz_risk_control(lot=abs(strategy_position_net)-abs(real_position_net))
                print(f'开空 {str(lot)} 手', end="  ")
                vt_orderids = self.short(vt_symbol=market_vt_symbol, price=sell_price, volume=lot, lock=True)
                print(f'vt_orderids: {vt_orderids}')

            elif abs(strategy_position_net) < abs(real_position_net):

                lot = TQZPositionData.tqz_risk_control(lot=abs(real_position_net) - abs(strategy_position_net))
                print(f'平空 {str(lot)} 手', end="  ")
                vt_orderids = self.cover(vt_symbol=market_vt_symbol, price=buy_price, volume=lot, lock=True)
                print(f'vt_orderids: {vt_orderids}')

            elif strategy_position_net is real_position_net:
                print(f'净仓相等, 不做处理')

        return vt_orderids

    def tqz_synchronization_position_double_direction_mode(self, market_vt_symbol, now_price, offset_price, strategy_position_buy, strategy_position_sell, real_position_buy, real_position_sell):

        buy_vt_orderids = []
        sell_vt_orderids = []
        buy_price = min(now_price + offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_up)
        sell_price = max(now_price - offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_down)

        interval = " | "
        print(market_vt_symbol, end="  ")
        if strategy_position_buy > real_position_buy:

            lot = TQZPositionData.tqz_risk_control(lot=strategy_position_buy - real_position_buy)
            print(f'开多 {str(lot)} 手', end="  ")
            buy_vt_orderids = self.buy(vt_symbol=market_vt_symbol, price=buy_price, volume=lot)
            print(f'buy_result: {buy_vt_orderids}', end=interval)

        elif strategy_position_buy < real_position_buy:

            lot = TQZPositionData.tqz_risk_control(lot=real_position_buy - strategy_position_buy)
            print(f'平多 {str(lot)} 手', end="  ")
            buy_vt_orderids = self.sell(vt_symbol=market_vt_symbol, price=sell_price, volume=lot)
            print(f'sell_result: {buy_vt_orderids}', end=interval)

        elif strategy_position_buy is real_position_buy:
            print("多单匹配 不处理", end=interval)

        if strategy_position_sell > real_position_sell:

            lot = TQZPositionData.tqz_risk_control(lot=strategy_position_sell - real_position_sell)
            print(f'开空 {str(lot)} 手', end="  ")
            sell_vt_orderids = self.short(vt_symbol=market_vt_symbol, price=sell_price, volume=lot)
            print(f'short_result: {sell_vt_orderids}')

        elif strategy_position_sell < real_position_sell:

            lot = TQZPositionData.tqz_risk_control(lot=real_position_sell - strategy_position_sell)
            print(f'平空 {str(lot)} 手', end="  ")
            sell_vt_orderids = self.cover(vt_symbol=market_vt_symbol, price=buy_price, volume=lot)
            print(f'cover_result: {sell_vt_orderids}')

        elif strategy_position_sell is real_position_sell:
            print("空单匹配 不处理")

        return list(set(buy_vt_orderids + sell_vt_orderids))

    def tqz_synchronization_position_min_netting_mode(self, market_vt_symbol, now_price, offset_price, strategy_position_buy, strategy_position_sell, real_position_buy, real_position_sell):
        """
        synchronization position in min netting with double direction(buy direction & sell direction) mode.
        """

        net_buy_abs = abs(strategy_position_buy - real_position_buy)
        net_sell_abs = abs(strategy_position_sell - real_position_sell)
        buy_vt_orderids = []
        sell_vt_orderids = []

        buy_price = min(now_price + offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_up)
        sell_price = max(now_price - offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_down)

        interval = " | "
        print(market_vt_symbol, end="  ")
        if net_buy_abs >= net_sell_abs:

            if strategy_position_buy < real_position_buy:
                lot = TQZPositionData.tqz_risk_control(lot=real_position_buy - strategy_position_buy)
                print(f'平多 {str(lot)} 手', end="  ")
                buy_vt_orderids = self.sell(vt_symbol=market_vt_symbol, price=sell_price, volume=lot)
                print(f'sell_result: {buy_vt_orderids}', end=interval)

            if strategy_position_sell > real_position_sell:
                lot = TQZPositionData.tqz_risk_control(lot=strategy_position_sell - real_position_sell)
                print(f'开空 {str(lot)} 手', end="  ")
                sell_vt_orderids = self.short(vt_symbol=market_vt_symbol, price=sell_price, volume=lot)
                print(f'short_result: {sell_vt_orderids}')

        else:

            if strategy_position_buy > real_position_buy:
                lot = TQZPositionData.tqz_risk_control(lot=strategy_position_buy - real_position_buy)
                print(f'开多 {str(lot)} 手', end="  ")
                buy_vt_orderids = self.buy(vt_symbol=market_vt_symbol, price=buy_price, volume=lot)
                print(f'buy_result: {buy_vt_orderids}', end=interval)

            if strategy_position_sell < real_position_sell:
                lot = TQZPositionData.tqz_risk_control(lot=real_position_sell - strategy_position_sell)
                print(f'平空 {str(lot)} 手', end="  ")
                sell_vt_orderids = self.cover(vt_symbol=market_vt_symbol, price=buy_price, volume=lot)
                print(f'cover_result: {sell_vt_orderids}')

        return list(set(buy_vt_orderids + sell_vt_orderids))

    def tqz_synchronization_position_net_mode(self, market_vt_symbol, now_price, offset_price, strategy_position_buy, strategy_position_sell, real_position_buy, real_position_sell):
        buy_vt_orderids = []
        sell_vt_orderids = []

        if strategy_position_buy > strategy_position_sell:
            strategy_position_buy, strategy_position_sell = strategy_position_buy - strategy_position_sell, 0
        elif strategy_position_buy < strategy_position_sell:
            strategy_position_sell, strategy_position_buy = strategy_position_sell - strategy_position_buy, 0
        elif strategy_position_buy is strategy_position_sell:
            strategy_position_buy, strategy_position_sell = 0, 0

        buy_price = min(now_price + offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_up)
        sell_price = max(now_price - offset_price, self.vt_symbols_limit_prices[market_vt_symbol].limit_down)

        interval = " | "
        print(market_vt_symbol, end="  ")
        if strategy_position_buy > real_position_buy:

            lot = TQZPositionData.tqz_risk_control(lot=strategy_position_buy - real_position_buy)
            print(f'开多 {str(lot)} 手', end="  ")
            buy_vt_orderids = self.buy(vt_symbol=market_vt_symbol, price=buy_price, volume=lot)
            print(f'buy_result: {buy_vt_orderids}', end=interval)

        elif strategy_position_buy < real_position_buy:

            lot = TQZPositionData.tqz_risk_control(lot=real_position_buy - strategy_position_buy)
            print(f'平多 {str(lot)} 手', end="  ")
            buy_vt_orderids = self.sell(vt_symbol=market_vt_symbol, price=sell_price, volume=lot)
            print(f'sell_result: {buy_vt_orderids}', end=interval)

        elif strategy_position_buy is real_position_buy:
            print("多单匹配 不处理", end=interval)

        if strategy_position_sell > real_position_sell:

            lot = TQZPositionData.tqz_risk_control(lot=strategy_position_sell - real_position_sell)
            print(f'开空 {str(lot)} 手', end="  ")
            sell_vt_orderids = self.short(vt_symbol=market_vt_symbol, price=sell_price, volume=lot)
            print(f'short_result: {sell_vt_orderids}')

        elif strategy_position_sell < real_position_sell:

            lot = TQZPositionData.tqz_risk_control(lot=real_position_sell - strategy_position_sell)
            print(f'平空 {str(lot)} 手', end="  ")
            sell_vt_orderids = self.cover(vt_symbol=market_vt_symbol, price=buy_price, volume=lot)
            print(f'cover_result: {sell_vt_orderids}')

        elif strategy_position_sell is real_position_sell:
            print("空单匹配 不处理")

        return list(set(buy_vt_orderids + sell_vt_orderids))

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


    def tqz_update_vt_symbols(self):
        """
        Update and Merge current strategy vt_symbols and real vt_symbols
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

        # path & content of path
        synchronize_position_path_setting_path = TQZFilePathOperator.grandfather_path(
            source_path=TQZFilePathOperator.current_file_grandfather_path(
                file=TQZFilePathOperator.current_file_father_path(file=__file__)
            )
        ) + '/.vntrader/synchronize_position_path_setting.json'
        synchronize_position_path_setting_content = TQZPositionJsonOperator.tqz_load_jsonfile(
            jsonfile=synchronize_position_path_setting_path
        )
        synchronize_strategy_paths = synchronize_position_path_setting_content[TQZSynchronizeSettingType.SYNCHRONIZE_STRATEGY_PATHS_KEY.value]

        # strategy content(sum)
        cta_data_list = [
            synchronize_strategy_paths[TQZSynchronizeSettingType.HLA_STRATEGY_PATH_KEY.value],
            synchronize_strategy_paths[TQZSynchronizeSettingType.HSR_STRATEGY_PATH_KEY.value]
        ]
        cta_sum_content = TQZPositionJsonOperator.tqz_get_sum_position_format_data(
            *cta_data_list
        )
        pair_trading_strategy_data = TQZPositionJsonOperator.tqz_get_ER_position_format_data(
            jsonfile=synchronize_strategy_paths[TQZSynchronizeSettingType.PAIR_TRADING_STRATEGY_PATH_KEY.value]
        )
        sum_content = TQZPositionJsonOperator.tqz_get_sum_position_format_data_with_jsonfileContentList(
            cta_sum_content,
            pair_trading_strategy_data
        )

        # multi
        multi_sum_content = TQZPositionJsonOperator.tqz_get_multi_format_data(
            format_content=sum_content,
            multi=synchronize_position_path_setting_content[TQZSynchronizeSettingType.MULTI_KEY.value]
        )

        # empty or not
        if synchronize_position_path_setting_content[TQZSynchronizeSettingType.NEED_CLEAR_POSITION_KEY.value] is True:
            multi_sum_content = TQZPositionJsonOperator.tqz_get_empty_format_data(format_content=multi_sum_content)

        return multi_sum_content

    @property
    def with_condition(self):
        return self

    def only_hold(self, hold_products: List[Product]):
        should_remove_vt_symbols = []

        for vt_symbol in self.vt_symbols:
            contract_data = self.strategy_engine.get_contract(vt_symbol=vt_symbol)
            if contract_data is None:
                should_remove_vt_symbols.append(vt_symbol)
            else:
                if contract_data.product not in hold_products:
                    should_remove_vt_symbols.append(vt_symbol)

        for vt_symbol in should_remove_vt_symbols:
            self.vt_symbols.remove(vt_symbol)


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
