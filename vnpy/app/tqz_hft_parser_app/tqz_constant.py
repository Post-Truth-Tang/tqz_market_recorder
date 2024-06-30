
from vnpy.trader.tqz_extern.tqz_constant import *


class TQZTradeLogTitles(Enum):
    """
    Titles of trade log.
    """

    CODE = "code"
    ORDER_TYPE = "order_type"
    ORDER_ID = "orderid"

    MARKET_PRICE_OF_SEND_ORDER = "market_price_of_send_order"
    MARKET_TIME_OF_SEND_ORDER = "market_time_of_send_order"

    SEND_ORDER_PRICE = "send_order_price"
    SEND_ORDER_TIME = "send_order_time"

    RECEIVE_TRADE_PRICE = "receive_trade_price"
    RECEIVE_TRADE_TIME = "receive_trade_time"

    LOTS = "lots"
    VOL_SCALE = "volScale"

    ORDER_COMMENT = "order_comment"

    SLIPPAGE = "slippage"
    SUM_SLIPPAGE = "sum_slippage"


class TQZOrderType(Enum):
    """
    Type of order.
    """

    BUY_ORDER_TYPE = "buy_order"
    SELL_ORDER_TYPE = "sell_order"
    SHORT_ORDER_TYPE = "short_order"
    COVER_ORDER_TYPE = "cover_order"


class TQZHftSheetType(Enum):
    """
    Type of hft sheet.
    """

    TOTAL = "total"
    DETAILED = "detailed"


class TQZHftMeritsTitles(Enum):
    """
    Titles of hft merits.
    """

    SUM_SLIPPAGE = "sum_slippage"
    CANCEL_ORDER_COUNTS = "cancel_order_counts"
    TRADE_TIMES = "trade_times"
    SEND_ORDER_TIMES = "send_order_times"
    PROFIT_AND_LOSS = "profit_and_loss"


class TQZOrderLogTitles(Enum):
    """
    Titles of order log.
    """

    CODE = "code"

    CANCEL_ORDER_COUNTS = "cancel_order_counts"