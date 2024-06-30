import re

from vnpy.trader.constant import Direction

from vnpy.trader.tqz_extern.tools.position_operator.position_operator import (
    TQZPositionKeyType
)

from vnpy.trader.tqz_extern.tqz_constant import (
    TQZFuturesType,
    TQZCffexSymbolType
)


class TQZSymbolOperator:

    @classmethod
    def tqz_get_strategy_position(cls, market_vt_symbol, direction: Direction, strategy_data):
        """ Get strategy position(buy, sell) """

        if market_vt_symbol in cls.tqz_get_strategy_vt_symbols(strategy_symbols=strategy_data.keys()):
            market_vt_symbol = cls.__find_strategy_symbol_with_vt_symbol(
                strategy_symbols=strategy_data.keys(),
                vt_symbol=market_vt_symbol
            )
            strategy_position = strategy_data[market_vt_symbol][cls.__tqz_direction(direction=direction)]
        else:
            strategy_position = 0

        return strategy_position

    @classmethod
    def tqz_synchronization_hint(cls, strategy_data, real_data, synchronization_vt_symbol):
        """ Return result of synchronization position """

        if cls.__strategyData_is_realData(strategy_data=strategy_data, real_data=real_data):
            hint = "持仓已同步完成"
        else:
            hint = "品种: " + str(synchronization_vt_symbol) + "  同步失败"

        return hint

    @staticmethod
    def get_vt_symbol(strategy_symbol):
        """ Get vt_symbol with strategy_symbol """

        return strategy_symbol.split(".")[0] + "." + strategy_symbol.split(".")[1]

    @staticmethod
    def get_vt_symbol_type(strategy_symbol):
        """ Get strategy type of vt_symbol with strategy_symbol """

        return strategy_symbol.split(".")[2]

    @staticmethod
    def get_sym(vt_symbol):
        return re.match(r"^[a-zA-Z]{1,3}", vt_symbol.split(".")[0]).group()

    @classmethod
    def tqz_marketVtSymbol_exsit_in_strategyData(cls, market_vt_symbol, strategy_data):
        """ Whether market_vt_symbol exsit in strategy data """

        return market_vt_symbol in cls.tqz_get_strategy_vt_symbols(strategy_symbols=strategy_data.keys())

    @classmethod
    def tqz_get_strategy_vt_symbols(cls, strategy_symbols):
        """ Get strategy vt_symbols with strategy_symbols """

        strategy_vt_symbols = []
        for strategy_symbol in strategy_symbols:
            vt_symbol = cls.get_vt_symbol(strategy_symbol=strategy_symbol)
            strategy_vt_symbols.append(vt_symbol)

        return strategy_vt_symbols

    @classmethod
    def tqz_get_futures_type(cls, vt_symbol):
        """ Get futures type of vt_symbol """

        sym = re.match(r"^[a-zA-Z]{1,3}", vt_symbol).group()

        if sym in [TQZCffexSymbolType.IC.value, TQZCffexSymbolType.IH.value, TQZCffexSymbolType.IF.value]:
            futures_type = TQZFuturesType.STOCK_INDEX_FUTURES
        elif sym in [TQZCffexSymbolType.T.value, TQZCffexSymbolType.TF.value, TQZCffexSymbolType.TS.value]:
            futures_type = TQZFuturesType.TREASURY_FUTURES
        else:
            futures_type = TQZFuturesType.COMMODITY_FUTURES

        return futures_type

    # --- private part ---
    @classmethod
    def __tqz_direction(cls, direction: Direction):
        if direction == Direction.LONG:
            tqz_direction = TQZPositionKeyType.BUY_POSITION_KEY.value
        elif direction == Direction.SHORT:
            tqz_direction = TQZPositionKeyType.SELL_POSITION_KEY.value
        elif direction == Direction.NET:
            tqz_direction = TQZPositionKeyType.NET_POSITION_KEY.value
        else:
            tqz_direction = ""

        return tqz_direction

    @classmethod
    def __strategyData_is_realData(cls, strategy_data, real_data):
        """ Whether strategy_data is real_data or not """

        # print("strategy_data:" + str(strategy_data), end=" | ")
        # print("real_data:" + str(real_data))

        all_symbols_is_same = None
        for vt_symbol in real_data.keys():

            strategy_position_temp = cls.tqz_get_strategy_position(
                market_vt_symbol=vt_symbol,
                direction=Direction.NET,
                strategy_data=strategy_data
            )

            if strategy_position_temp is real_data[vt_symbol]:
                all_symbols_is_same = strategy_position_temp is real_data[vt_symbol]
                continue
            else:
                all_symbols_is_same = strategy_position_temp is real_data[vt_symbol]
                break

        return all_symbols_is_same


    @classmethod
    def __marketVtSymbol_not_in_strategyData(cls, market_vt_symbol, strategy_data):
        """ Whether market_vt_symbol not in strategy_data or not """

        return not cls.tqz_marketVtSymbol_exsit_in_strategyData(
            market_vt_symbol=market_vt_symbol,
            strategy_data=strategy_data.keys()
        )

    @classmethod
    def __find_strategy_symbol_with_vt_symbol(cls, strategy_symbols, vt_symbol):
        """ Find strategy symbol(vt_symbol_type), return None when strategy symbol(vt_symbol_type) not in strategy datas """

        find_strategy_symbol = None
        for strategy_symbol in strategy_symbols:
            strategy_vt_symbol = cls.get_vt_symbol(strategy_symbol=strategy_symbol)
            if vt_symbol == strategy_vt_symbol:
                find_strategy_symbol = strategy_symbol

        return find_strategy_symbol


def __futures_type_test():

    stock_index_vt_symbols = [
        "IC2106.CFFEX",
        "IF2106.CFFEX",
        "IH2106.CFFEX",
        "j2111.DCE",
        "SR111.CZCE",
        "SA111.CZCE",
    ]

    for vt_symbol in stock_index_vt_symbols:
        futures_type = TQZSymbolOperator.tqz_get_futures_type(vt_symbol=vt_symbol)
        print("futures_type: " + str(futures_type), end="  ")
        print("vt_symbol: " + str(vt_symbol))


if __name__ == '__main__':
    __futures_type_test()
