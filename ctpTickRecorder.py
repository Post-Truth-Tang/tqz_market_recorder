import sys
import multiprocessing
import re
from copy import copy
from vnpy.trader.constant import Exchange
from vnpy.trader.object import BarData, TickData
from enum import Enum
from time import sleep
from datetime import datetime, time
from logging import INFO

from vnpy.event import EventEngine
from vnpy.trader.setting import SETTINGS
from vnpy.trader.engine import MainEngine
from vnpy.trader.utility import extract_vt_symbol

from vnpy.gateway.ctp import CtpGateway
from vnpy.app.cta_strategy.base import EVENT_CTA_LOG
from vnpy.app.data_recorder.engine import RecorderEngine

from vnpy.trader.tqz_extern.tools.position_operator.position_operator import TQZJsonOperator
from vnpy.trader.tqz_extern.tools.file_path_operator.file_path_operator import TQZFilePathOperator

EXCHANGE_LIST = [
    Exchange.SHFE,
    Exchange.DCE,
    Exchange.CZCE,
    Exchange.CFFEX,
    Exchange.INE,
]

SETTINGS["log.active"] = True
SETTINGS["log.level"] = INFO
SETTINGS["log.console"] = True
CTP_SETTING = {
    "用户名": "8010101191",
    "密码": "sc#860901",
    "经纪商代码": "4500",
    "交易服务器": "180.166.45.116:41305",
    "行情服务器": "180.166.45.116:41313",
    "产品名称": "client_fxtrader_1.0",
    "授权编码": "V7F3D52TDCZOL7LM",
    "产品信息": ""
}

def is_futures(vt_symbol: str) -> bool:
    """
    是否是期货
    """
    return bool(re.match(r"^[a-zA-Z]{1,3}\d{2,4}.[A-Z]+$", vt_symbol))


def is_hft(vt_symbol: str) -> bool:
    # strategies_path = "strategies.json"
    strategies_path = TQZFilePathOperator.father_path(source_path=__file__) + f'/strategies.json'
    content = TQZJsonOperator.tqz_load_jsonfile(jsonfile=strategies_path)

    code_list = []
    [code_list.append(hft_strategy['params']['code']) for hft_strategy in content['strategies']['hft']]

    vt_symbol_list = []
    for code in code_list:
        exchange = code.split('.')[0]
        symbol = code.split('.')[1]
        year_month = code.split('.')[2]
        if exchange == 'CZCE':
            year_month = int(year_month) % 1000
        vt_symbol_list.append(f'{symbol}{year_month}.{exchange}')

    return vt_symbol in vt_symbol_list


class RecordMode(Enum):
    BAR = "bar"
    TICK = "tick"

class WholeMarketRecorder(RecorderEngine):
    def __init__(self, main_engine, event_engine, record_modes=[RecordMode.TICK]):
        super().__init__(main_engine, event_engine)
        self.record_modes = record_modes
        # 非交易时间
        self.drop_start = time(3, 15)
        self.drop_end = time(8, 45)

        # 大连、上海、郑州交易所，小节休息
        self.rest_start = time(10, 15)
        self.rest_end = time(10, 30)

    def istrading(self, vt_symbol, current_time) -> bool:
        """
        交易时间，过滤校验Tick
        """
        symbol, exchange = extract_vt_symbol(vt_symbol)

        if self.drop_start <= current_time < self.drop_end:
            return False
        if exchange in [Exchange.DCE, Exchange.SHFE, Exchange.CZCE]:
            if self.rest_start <= current_time < self.rest_end:
                return False
        return True

    def load_setting(self):
        pass

    def record_tick(self, tick: TickData):
        """
        抛弃非交易时间校验数据
        """
        tick_time = tick.datetime.time()
        if not self.istrading(tick.vt_symbol, tick_time):
            return
        task = ("tick", copy(tick))
        # print("在录tick")
        self.queue.put(task)

    def record_bar(self, bar: BarData):
        """
        抛弃非交易时间校验数据
        """
        bar_time = bar.datetime.time()
        if not self.istrading(bar.vt_symbol, bar_time):
            return
        task = ("bar", copy(bar))
        self.queue.put(task)

    def process_contract_event(self, event):
        """"""
        contract = event.data
        vt_symbol = contract.vt_symbol
        # 不录制期权 & 只录制hft合约
        if is_futures(vt_symbol) and is_hft(vt_symbol=vt_symbol):
            if RecordMode.BAR in self.record_modes:
                self.add_bar_recording(vt_symbol)
            if RecordMode.TICK in self.record_modes:
                self.add_tick_recording(vt_symbol)
            self.subscribe(contract)


def run_child():
    """
    Running in the child process.
    """
    SETTINGS["log.file"] = True

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(CtpGateway)
    main_engine.write_log("主引擎创建成功")

    # 记录引擎
    log_engine = main_engine.get_engine("log")
    event_engine.register(EVENT_CTA_LOG, log_engine.process_log_event)
    main_engine.write_log("注册日志事件监听")

    main_engine.connect(CTP_SETTING, "CTP")
    main_engine.write_log("连接 ctp 接口")

    whole_market_recorder = WholeMarketRecorder(main_engine, event_engine)

    main_engine.write_log("开始录制数据")
    oms_engine = main_engine.get_engine("oms")
    while True:
        sleep(1)


def run_parent():
    """
    Running in the parent process.
    """
    print("启动dataRecord策略守护父进程")

    # Chinese futures market trading period (day/night)
    MORNING_START = time(8, 45)
    MORNING_END = time(12, 0)

    AFTERNOON_START = time(12, 45)
    AFTERNOON_END = time(15, 35)

    NIGHT_START = time(20, 45)
    NIGHT_END = time(3, 5)

    child_process = None

    while True:
        current_time = datetime.now().time()
        trading = False

        # Check whether in trading period
        if (
            (MORNING_START <= current_time <= MORNING_END)
            or (AFTERNOON_START <= current_time <= AFTERNOON_END)
            or (current_time >= NIGHT_START)
            or (current_time <= NIGHT_END)
        ):
            trading = True
        else:
            # print("非录制时间")
            pass
        
        # Start child process in trading period
        if trading and child_process is None:
            print("启动数据录制子进程")
            child_process = multiprocessing.Process(target=run_child)
            child_process.start()
            print("数据录制子进程启动成功")

        # 非记录时间则退出数据录制子进程
        if not trading and child_process is not None:
            print("关闭数据录制子进程")
            child_process.terminate()
            child_process.join()
            child_process = None
            print("数据录制子进程关闭成功")
        sys.stdout.flush()
        sleep(5)


if __name__ == "__main__":
    run_parent()