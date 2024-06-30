from pathlib import Path

from vnpy.trader.app import BaseApp
from vnpy.trader.constant import Direction
from vnpy.trader.object import TickData, BarData, TradeData, OrderData
from vnpy.trader.utility import BarGenerator, ArrayManager

# from .engine import RecorderEngine, APP_NAME
from .tqz_record_engine import TQZRecodeEngine, APP_NAME

class DataRecorderApp(BaseApp):
    """"""
    app_name = APP_NAME
    app_module = __module__
    app_path = Path(__file__).parent
    display_name = "行情记录"
    engine_class = TQZRecodeEngine
    widget_name = "RecorderManager"
    icon_name = "recorder.ico"
