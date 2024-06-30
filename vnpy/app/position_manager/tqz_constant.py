
from vnpy.trader.tqz_extern.tqz_constant import *


# --- synchronize position part ---
class TQZSynchronizeSettingType(Enum):
    """
    Type of synchronize-strategy-setting key
    """

    SYNCHRONIZE_STRATEGY_PATHS_KEY = "synchronize_strategy_paths"

    HLA_STRATEGY_PATH_KEY = "hla_strategy_path"
    HSR_STRATEGY_PATH_KEY = "hsr_strategy_path"
    PAIR_TRADING_STRATEGY_PATH_KEY = "pair_trading_strategy_path"

    MULTI_KEY = "multi"
    NEED_CLEAR_POSITION_KEY = "need_clear_position"


class TQZSynchronizeTimesKey(Enum):
    """
    Key of synchronize times
    """

    BUY_SYNCHRONIZE_TIMES = "buy_synchronize_times"
    SELL_SYNCHRONIZE_TIMES = "sell_synchronize_times"
    SHORT_SYNCHRONIZE_TIMES = "short_synchronize_times"
    COVER_SYNCHRONIZE_TIMES = "cover_synchronize_times"


class TQZOrderSendType(Enum):
    """
    Type of send order
    """

    BUY = "buy_synchronize_times"
    SELL = "sell_synchronize_times"
    SHORT = "short_synchronize_times"
    COVER = "cover_synchronize_times"