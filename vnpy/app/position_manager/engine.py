import importlib
import os
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Type, Any, Callable, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from tzlocal import get_localzone

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.object import (
    OrderRequest,
    SubscribeRequest,
    HistoryRequest,
    LogData,
    TickData,
    OrderData,
    TradeData,
    PositionData,
    BarData,
    ContractData
)
from vnpy.trader.event import (
    EVENT_TICK,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_POSITION,
    EVENT_CONTRACT,
    EVENT_ACCOUNT
)
from vnpy.trader.constant import (
    Direction,
    OrderType,
    Interval,
    Offset,
    Product,
    Status
)
from vnpy.trader.utility import extract_vt_symbol, round_to
from vnpy.trader.database import database_manager
from vnpy.trader.converter import OffsetConverter

from .base import (
    APP_NAME,
    EVENT_PORTFOLIO_LOG,
    EVENT_PORTFOLIO_STRATEGY
)
from .template import StrategyTemplate

from vnpy.trader.tqz_extern.tools.position_data.position_data import TQZPositionData
from vnpy.trader.tqz_extern.tools.position_operator.position_operator import TQZJsonOperator
from vnpy.trader.tqz_extern.tools.file_path_operator.file_path_operator import TQZFilePathOperator
from vnpy.trader.tqz_extern.tools.symbol_operator.symbol_operator import TQZSymbolOperator

from vnpy.trader.tqz_extern.tqz_object import TQZAccountData


class StrategyEngine(BaseEngine):
    """"""

    setting_filename = TQZFilePathOperator.current_file_grandfather_path(
        file=TQZFilePathOperator.grandfather_path(source_path=__file__)
    ) + f'/.vntrader/position_manager_setting.json'

    data_filename = TQZFilePathOperator.current_file_grandfather_path(
        file=TQZFilePathOperator.grandfather_path(source_path=__file__)
    ) + f'/.vntrader/position_manager_data.json'


    strategy_positions_all_path = TQZFilePathOperator.grandfather_path(
        source_path=TQZFilePathOperator.grandfather_path(source_path=__file__)
    ) + f'/.vntrader/sum_WYTZ.json'

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super().__init__(main_engine, event_engine, APP_NAME)

        self.strategy_data: Dict[str, Dict] = {}

        self.classes: Dict[str, Type[StrategyTemplate]] = {}
        self.strategies: Dict[str, StrategyTemplate] = {}

        self.symbol_strategy_map: Dict[str, List[StrategyTemplate]] = defaultdict(list)
        self.orderid_strategy_map: Dict[str, StrategyTemplate] = {}

        self.accounts: Dict[str, TQZAccountData] = {}
        # 账户所有持仓数据
        self.positions: Dict[str, PositionData] = {}
        # 所有合约数据
        self.contracts: Dict[str, ContractData] = {}
        # 市场全品种
        self.all_vt_symbols = []
        # 账户当前挂单
        self.all_active_orders: Dict[str, OrderData] = {}

        self.init_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)

        self.vt_tradeids: Set[str] = set()
        self.offset_converter: OffsetConverter = OffsetConverter(self.main_engine)


        self.add_function()
        self.register_event()


    def add_function(self):
        self.main_engine.get_position = self.get_position
        self.main_engine.get_all_positions = self.get_all_positions
        self.main_engine.get_contract = self.get_contract
        self.main_engine.get_all_contracts = self.get_all_contracts

    def get_position(self, vt_positionid: object) -> object:
        """
        Get latest position data by vt_positionid.
        """
        return self.positions.get(vt_positionid, None)

    def get_all_positions(self) -> List[PositionData]:
        """
        Get all position data.
        """
        return list(self.positions.values())

    def get_contract(self, vt_symbol: str) -> Optional[ContractData]:
        """
        Get contract data by vt_symbol.
        """
        return self.contracts.get(vt_symbol, None)

    def get_all_contracts(self) -> List[ContractData]:
        """
        Get all contract data.
        """
        return list(self.contracts.values())

    def init_engine(self):
        """
        """
        self.register_event()
        self.load_strategy_class()
        self.load_strategy_setting()
        self.load_strategy_data()
        self.write_log("仓位管理策略引擎初始化成功")

    def close(self):
        """"""
        self.stop_all_strategies()

    def register_event(self):
        """"""

        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_ORDER, self.process_order_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)
        self.event_engine.register(EVENT_POSITION, self.process_position_event)
        self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)
        self.event_engine.register(EVENT_ACCOUNT, self.process_account_event)


    def process_account_event(self, event: Event) -> None:
        """ """
        account = event.data

        self.accounts[account.vt_accountid] = TQZAccountData(
            gateway_name=account.gateway_name,
            accountid=account.accountid,
            balance=account.balance,
            frozen=account.frozen
        )

    def process_contract_event(self, event: Event) -> None:
        """"""
        contract = event.data

        if contract.product in [Product.FUTURES]:
            self.contracts[contract.vt_symbol] = contract
            self.all_vt_symbols.append(contract.vt_symbol)

    def process_tick_event(self, event: Event):
        """"""
        tick: TickData = event.data

        strategies = self.symbol_strategy_map[tick.vt_symbol]

        if not strategies:
            return

        for strategy in strategies:
            if strategy.inited:
                self.call_strategy_func(strategy, strategy.on_tick, tick)

    def process_order_event(self, event: Event):
        """ """
        order: OrderData = event.data

        self.offset_converter.update_order(order)
        strategy = self.orderid_strategy_map.get(order.vt_orderid, None)

        if not strategy:
            return

        if not order.is_active():
            strategy.active_orderids.remove(order.vt_orderid)
            self.orderid_strategy_map.pop(order.vt_orderid)

        self.call_strategy_func(strategy, strategy.on_order, order)

    def process_trade_event(self, event: Event):
        """"""
        trade: TradeData = event.data

        # Filter duplicate trade push
        if trade.vt_tradeid in self.vt_tradeids:
            return
        self.vt_tradeids.add(trade.vt_tradeid)

        self.offset_converter.update_trade(trade)

        strategy = self.orderid_strategy_map.get(trade.vt_orderid, None)
        if not strategy:
            return

        self.call_strategy_func(strategy, strategy.on_trade, trade)

    def process_position_event(self, event: Event) -> None:
        """"""
        position = event.data
        self.positions[position.vt_positionid] = position
        self.offset_converter.update_position(position)

        TQZPositionData.tqz_update_position_datas(new_position_datas=self.positions)

    def send_order(
        self,
        strategy: StrategyTemplate,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float,
        lock: bool
    ):
        """
        Send a new order to server.
        """
        contract: ContractData = self.main_engine.get_contract(vt_symbol)
        if not contract:
            self.write_log(f"委托失败，找不到合约：{vt_symbol}", strategy)
            return ""

        # Round order price and volume to nearest incremental value
        price = round_to(price, contract.pricetick)
        volume = round_to(volume, contract.min_volume)

        # Create request and send order.
        original_req = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            offset=offset,
            type=OrderType.LIMIT,
            price=price,
            volume=volume,
        )

        # Convert with offset converter
        req_list = self.offset_converter.convert_order_request(original_req, lock)

        # Send Orders
        vt_orderids = []

        for req in req_list:
            req.reference = strategy.strategy_name      # Add strategy name as order reference

            vt_orderid = self.main_engine.send_order(req, contract.gateway_name)

            # Check if sending order successful
            if not vt_orderid:
                continue

            vt_orderids.append(vt_orderid)

            self.offset_converter.update_order_request(req, vt_orderid)

            # Save relationship between orderid and strategy.
            self.orderid_strategy_map[vt_orderid] = strategy

        return vt_orderids

    def cancel_order(self, strategy: StrategyTemplate, vt_orderid: str):
        """
        """
        order = self.main_engine.get_active_order(vt_orderid)
        if not order:
            self.write_log(f"撤单失败，找不到委托{vt_orderid}", strategy)
            return

        req = order.create_cancel_request()
        self.main_engine.cancel_order(req, order.gateway_name)

    def call_strategy_func(self, strategy: StrategyTemplate, func: Callable, params: Any = None):
        """
        Call function of a strategy and catch any exception raised.
        """
        try:
            if params:
                func(params)
            else:
                func()
        except Exception:
            strategy.trading = False
            strategy.inited = False

            msg = f"触发异常已停止\n{traceback.format_exc()}"
            self.write_log(msg, strategy)

    def load_bars(self, strategy: StrategyTemplate, days: int, interval: Interval):
        """"""
        vt_symbols = strategy.vt_symbols
        dts: Set[datetime] = set()
        history_data: Dict[Tuple, BarData] = {}

        # Load data from rqdata/gateway/database
        for vt_symbol in vt_symbols:
            data = self.load_bar(vt_symbol, days, interval)

            for bar in data:
                dts.add(bar.datetime)
                history_data[(bar.datetime, vt_symbol)] = bar

        # Convert data structure and push to strategy
        dts = list(dts)
        dts.sort()

        bars = {}

        for dt in dts:
            for vt_symbol in vt_symbols:
                bar = history_data.get((dt, vt_symbol), None)

                # If bar data of vt_symbol at dt exists
                if bar:
                    bars[vt_symbol] = bar
                # Otherwise, use previous data to backfill
                elif vt_symbol in bars:
                    old_bar = bars[vt_symbol]

                    bar = BarData(
                        symbol=old_bar.symbol,
                        exchange=old_bar.exchange,
                        datetime=dt,
                        open_price=old_bar.close_price,
                        high_price=old_bar.close_price,
                        low_price=old_bar.close_price,
                        close_price=old_bar.close_price,
                        gateway_name=old_bar.gateway_name
                    )
                    bars[vt_symbol] = bar

            self.call_strategy_func(strategy, strategy.on_bars, bars)

    def load_bar(self, vt_symbol: str, days: int, interval: Interval) -> List[BarData]:
        """"""
        symbol, exchange = extract_vt_symbol(vt_symbol)
        end = datetime.now(get_localzone())
        start = end - timedelta(days)
        contract: ContractData = self.main_engine.get_contract(vt_symbol)
        data = []

        # Query bars from gateway if available
        if contract and contract.history_data:
            req = HistoryRequest(symbol=symbol, exchange=exchange, interval=interval, start=start, end=end)
            data = self.main_engine.query_history(req, contract.gateway_name)
        # Try to query bars from RQData, if not found, load from database.
        else:
            data = self.query_bar_from_rq(symbol, exchange, interval, start, end)

        if not data:
            data = database_manager.load_bar_data(symbol=symbol, exchange=exchange, interval=interval, start=start, end=end)

        return data

    def add_strategy(self, class_name: str, strategy_name: str, vt_symbols: list, setting: dict):
        """
        Add a new strategy.
        """
        if strategy_name in self.strategies:
            self.write_log(f"创建策略失败，存在重名{strategy_name}")
            return

        strategy_class = self.classes.get(class_name, None)
        if not strategy_class:
            self.write_log(f"创建策略失败，找不到策略类{class_name}")
            return

        strategy = strategy_class(self, strategy_name, vt_symbols, setting)
        self.strategies[strategy_name] = strategy

        # Add vt_symbol to strategy map.
        for vt_symbol in vt_symbols:
            strategies = self.symbol_strategy_map[vt_symbol]
            strategies.append(strategy)

        self.save_strategy_setting()
        self.put_strategy_event(strategy)

    def init_strategy(self, strategy_name: str):
        """
        Init a strategy.
        """
        self.init_executor.submit(self._init_strategy, strategy_name)

    def _init_strategy(self, strategy_name: str):
        """
        Init strategies in queue.
        """
        strategy = self.strategies[strategy_name]

        if strategy.inited:
            self.write_log(f"{strategy_name}已经完成初始化，禁止重复操作")
            return

        self.write_log(f"{strategy_name}开始执行初始化")

        # Call on_init function of strategy
        self.call_strategy_func(strategy, strategy.on_init)

        # Restore strategy data(variables)
        data = self.strategy_data.get(strategy_name, None)
        if data:
            for name in strategy.variables:
                value = data.get(name, None)
                if name == "pos":
                    pos = getattr(strategy, name)
                    pos.update(value)
                elif value:
                    setattr(strategy, name, value)

        # Subscribe market data
        for vt_symbol in strategy.vt_symbols:
            contract: ContractData = self.main_engine.get_contract(vt_symbol)
            if contract:
                req = SubscribeRequest(
                    symbol=contract.symbol, exchange=contract.exchange)
                self.main_engine.subscribe(req, contract.gateway_name)
            else:
                self.write_log(f"行情订阅失败，找不到合约{vt_symbol}", strategy)

        # Put event to update init completed status.
        strategy.inited = True
        self.put_strategy_event(strategy)
        self.write_log(f"{strategy_name}初始化完成")

    def start_strategy(self, strategy_name: str):
        """
        Start a strategy.
        """
        strategy = self.strategies[strategy_name]
        if not strategy.inited:
            self.write_log(f"策略{strategy.strategy_name}启动失败，请先初始化")
            return

        if strategy.trading:
            self.write_log(f"{strategy_name}已经启动，请勿重复操作")
            return

        self.call_strategy_func(strategy, strategy.on_start)
        strategy.trading = True

        self.put_strategy_event(strategy)

    def stop_strategy(self, strategy_name: str):
        """
        Stop a strategy.
        """
        strategy = self.strategies[strategy_name]
        if not strategy.trading:
            return

        # Call on_stop function of the strategy
        self.call_strategy_func(strategy, strategy.on_stop)

        # Change trading status of strategy to False
        strategy.trading = False

        # Cancel all orders of the strategy
        strategy.cancel_all()

        # Sync strategy variables to data file
        self.sync_strategy_data(strategy)

        # Update GUI
        self.put_strategy_event(strategy)

    def edit_strategy(self, strategy_name: str, setting: dict):
        """
        Edit parameters of a strategy.
        """
        strategy = self.strategies[strategy_name]
        strategy.update_setting(setting)

        self.save_strategy_setting()
        self.put_strategy_event(strategy)

    def remove_strategy(self, strategy_name: str):
        """
        Remove a strategy.
        """
        strategy = self.strategies[strategy_name]
        if strategy.trading:
            self.write_log(f"策略{strategy.strategy_name}移除失败，请先停止")
            return

        # Remove from symbol strategy map
        for vt_symbol in strategy.vt_symbols:
            strategies = self.symbol_strategy_map[vt_symbol]
            strategies.remove(strategy)

        # Remove from vt_orderid strategy map
        for vt_orderid in strategy.active_orderids:
            if vt_orderid in self.orderid_strategy_map:
                self.orderid_strategy_map.pop(vt_orderid)

        # Remove from strategies
        self.strategies.pop(strategy_name)
        self.save_strategy_setting()

        return True

    def load_strategy_class(self):
        """
        Load strategy class from source code.
        """
        path1 = Path(__file__).parent.joinpath("strategies")

        self.load_strategy_class_from_folder(path1, "vnpy.app.position_manager.strategies")
        path2 = Path.cwd().joinpath("strategies")
        self.load_strategy_class_from_folder(path2, "strategies")

    def load_strategy_class_from_folder(self, path: Path, module_name: str = ""):
        """
        Load strategy class from certain folder.
        """
        for dirpath, dirnames, filenames in os.walk(str(path)):
            for filename in filenames:
                if filename.endswith(".py"):
                    strategy_module_name = ".".join(
                        [module_name, filename.replace(".py", "")])
                elif filename.endswith(".pyd"):
                    strategy_module_name = ".".join(
                        [module_name, filename.split(".")[0]])
                else:
                    continue

                self.load_strategy_class_from_module(strategy_module_name)

    def load_strategy_class_from_module(self, module_name: str):
        """
        Load strategy class from module file.
        """
        try:
            module = importlib.import_module(module_name)

            for name in dir(module):
                value = getattr(module, name)
                if isinstance(value, type) and issubclass(value, StrategyTemplate) and value is not StrategyTemplate:
                    self.classes[value.__name__] = value
        except:  # noqa
            msg = f"策略文件{module_name}加载失败，触发异常：\n{traceback.format_exc()}"
            self.write_log(msg)

    def load_strategy_data(self):
        """
        Load strategy data from json file.
        """
        self.strategy_data = TQZJsonOperator.tqz_load_jsonfile(jsonfile=self.data_filename)

    def sync_strategy_data(self, strategy: StrategyTemplate):
        """
        Sync strategy data into json file.
        """
        data = strategy.get_variables()
        data.pop("inited")      # Strategy status (inited, trading) should not be synced.
        data.pop("trading")

        self.strategy_data[strategy.strategy_name] = data
        TQZJsonOperator.tqz_write_jsonfile(content=self.strategy_data, target_jsonfile=self.data_filename)

    def get_all_strategy_class_names(self):
        """
        Return names of strategy classes loaded.
        """
        return list(self.classes.keys())

    def get_strategy_class_parameters(self, class_name: str):
        """
        Get default parameters of a strategy class.
        """
        strategy_class = self.classes[class_name]

        parameters = {}
        for name in strategy_class.parameters:
            parameters[name] = getattr(strategy_class, name)

        return parameters

    def get_strategy_parameters(self, strategy_name):
        """
        Get parameters of a strategy.
        """
        strategy = self.strategies[strategy_name]
        return strategy.get_parameters()

    def init_all_strategies(self):
        """
        """
        for strategy_name in self.strategies.keys():
            self.init_strategy(strategy_name)

    def start_all_strategies(self):
        """
        """
        for strategy_name in self.strategies.keys():
            self.start_strategy(strategy_name)

    def stop_all_strategies(self):
        """
        """
        for strategy_name in self.strategies.keys():
            self.stop_strategy(strategy_name)

    def load_strategy_setting(self):
        """
        Load setting file.
        """
        strategy_setting = TQZJsonOperator.tqz_load_jsonfile(jsonfile=self.setting_filename)

        total_vt_symbols = self.__get_total_vt_symbols(
            strategy_positions_all_path=self.strategy_positions_all_path,
            real_positions=self.positions
        )

        for strategy_name, strategy_config in strategy_setting.items():
            self.add_strategy(
                strategy_config["class_name"],
                strategy_name,
                total_vt_symbols,
                strategy_config["setting"]
            )

    def __get_total_vt_symbols(self, strategy_positions_all_path: str, real_positions) -> list:
        """
        Get total vt_symbols with real vt_symbols and strategy vt_symbols.
        """

        strategy_data = TQZJsonOperator.tqz_load_jsonfile(jsonfile=strategy_positions_all_path)
        strategy_vt_symbols = list(set(TQZSymbolOperator.tqz_get_strategy_vt_symbols(strategy_symbols=strategy_data.keys())))
        real_vt_symbols = list(set(TQZSymbolOperator.tqz_get_strategy_vt_symbols(strategy_symbols=real_positions.keys())))

        total_vt_symbols = []
        for vt_symbol in list(set(strategy_vt_symbols + real_vt_symbols)):
            if vt_symbol in self.contracts.keys():
                total_vt_symbols.append(vt_symbol)
            else:
                print(f'{vt_symbol} not in contracts.')

        return total_vt_symbols

    def save_strategy_setting(self):
        """
        Save setting file.
        """
        strategy_setting = {}

        for name, strategy in self.strategies.items():
            strategy_setting[name] = {
                "class_name": strategy.__class__.__name__,
                "vt_symbols": strategy.vt_symbols,
                "setting": strategy.get_parameters()
            }

        TQZJsonOperator.tqz_write_jsonfile(content=strategy_setting, target_jsonfile=self.setting_filename)

    def put_strategy_event(self, strategy: StrategyTemplate):
        """
        Put an event to update strategy status.
        """
        data = strategy.get_data()
        event = Event(EVENT_PORTFOLIO_STRATEGY, data)
        self.event_engine.put(event)

    def write_log(self, msg: str, strategy: StrategyTemplate = None):
        """
        Create portfolio engine log event.
        """
        if strategy:
            msg = f"{strategy.strategy_name}: {msg}"

        log = LogData(msg=msg, gateway_name=APP_NAME)
        event = Event(type=EVENT_PORTFOLIO_LOG, data=log)
        self.event_engine.put(event)

    def send_email(self, msg: str, strategy: StrategyTemplate = None):
        """
        Send email to default receiver.
        """
        if strategy:
            subject = f"{strategy.strategy_name}"
        else:
            subject = "仓位管理策略引擎"

        self.main_engine.send_email(subject, msg)

    def get_pricetick(self, vt_symbol: str):
        """
        Return contract pricetick data.
        """
        contract: ContractData = self.main_engine.get_contract(vt_symbol)

        if contract:
            return contract.pricetick
        else:
            return None

    def get_bigpointvalue(self, vt_symbol: str):
        """
        Return contract pricetick data.
        """
        contract: ContractData = self.main_engine.get_contract(vt_symbol)

        if contract:
            return contract.size
        else:
            return None