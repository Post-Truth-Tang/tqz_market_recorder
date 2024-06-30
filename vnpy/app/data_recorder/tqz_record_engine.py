from vnpy.app.data_recorder.engine import RecorderEngine
from vnpy.trader.engine import MainEngine
from vnpy.event import Event, EventEngine

from queue import Queue
from threading import Thread

from vnpy.trader.event import EVENT_TICK, EVENT_CONTRACT

from vnpy.app.data_recorder.tqz_constant import RECORD_MODE, Exchange, Product


APP_NAME = "TQZDataRecorder"


class TQZRecodeEngine(RecorderEngine):

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super().__init__(main_engine, event_engine)

        self.queue = Queue()
        self.thread = Thread(target=self.run)
        self.active = False

        self.strategies = {}

        self.record_modes = [RECORD_MODE.TICK_MODE]  # data.json content.

        self.register_event()
        self.start()


    def register_event(self):
        """"""
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)

    def process_tick_event(self, event: Event):
        """"""
        tick = event.data
        self.update_tick(tick)

    def process_contract_event(self, event: Event):
        """"""
        contract = event.data
        vt_symbol = contract.vt_symbol

        if contract.product in [Product.FUTURES]:
            if RECORD_MODE.BAR_MODE in self.record_modes:
                self.add_bar_recording(vt_symbol)
            if RECORD_MODE.TICK_MODE in self.record_modes:
                self.add_tick_recording(vt_symbol)
            self.subscribe(contract)

    def add_bar_recording(self, vt_symbol: str):
        """"""
        if vt_symbol in self.bar_recordings:
            self.write_log(f"已在K线记录列表中：{vt_symbol}")
            return

        if Exchange.LOCAL.value not in vt_symbol:
            contract = self.main_engine.get_contract(vt_symbol)
            if not contract:
                self.write_log(f"找不到合约：{vt_symbol}")
                return

            self.bar_recordings[vt_symbol] = {
                "symbol": contract.symbol,
                "exchange": contract.exchange.value,
                "gateway_name": contract.gateway_name
            }

            self.subscribe(contract)
        else:
            self.tick_recordings[vt_symbol] = {}

        self.save_setting()
        self.put_event()

        self.write_log(f"添加K线记录成功：{vt_symbol}")


    def add_tick_recording(self, vt_symbol: str):
        """"""
        if vt_symbol in self.tick_recordings:
            self.write_log(f"已在Tick记录列表中：{vt_symbol}")
            return

        # For normal contract
        if Exchange.LOCAL.value not in vt_symbol:
            contract = self.main_engine.get_contract(vt_symbol)
            if not contract:
                self.write_log(f"找不到合约：{vt_symbol}")
                return

            self.tick_recordings[vt_symbol] = {
                "symbol": contract.symbol,
                "exchange": contract.exchange.value,
                "gateway_name": contract.gateway_name
            }

            self.subscribe(contract)
        # No need to subscribe for spread data
        else:
            self.tick_recordings[vt_symbol] = {}

        self.save_setting()
        self.put_event()

        self.write_log(f"添加Tick记录成功：{vt_symbol}")


    def init_engine(self):
        pass

    def init_all_strategies(self):
        pass

    def start_all_strategies(self):
        pass
