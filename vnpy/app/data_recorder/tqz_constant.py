
from vnpy.trader.constant import *


class RECORD_PRODUCT(Enum):
    """
    record product.
    """

    FUTURES = "期货"
    OPTION = "期权"

    FUTURES_OPTION = "期货&期权"


class RECORD_MODE(Enum):
    """
    Type of record (tick & bar).
    """

    TICK_MODE = "tick_mode"
    BAR_MODE = "bar_mode"
