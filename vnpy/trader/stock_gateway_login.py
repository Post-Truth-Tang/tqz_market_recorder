import multiprocessing
import sys
import os
from time import sleep
from datetime import datetime, time
from logging import INFO
from typing import Type

from vnpy.event import EventEngine
from vnpy.trader.setting import SETTINGS
from vnpy.trader.engine import MainEngine
from vnpy.trader.app import BaseApp

from vnpy.app.cta_strategy.base import EVENT_CTA_LOG

from vnpy.trader.gateway import BaseGateway

from vnpy.gateway.xtp import XtpGateway
from vnpy.app.cta_strategy import CtaStrategyApp
from vnpy.app.position_manager import PositionManagerApp
from vnpy.app.tqz_data_dump_app import TQZDataDumpApp

from vnpy.trader.tqz_extern.tools.position_operator.position_operator import TQZJsonOperator
from vnpy.trader.tqz_extern.tools.file_path_operator.file_path_operator import TQZFilePathOperator
from vnpy.trader.tqz_extern.tqz_constant import TQZStockGatewaySettingKey

SETTINGS["log.active"] = True
SETTINGS["log.level"] = INFO
SETTINGS["log.console"] = True


class TQZGatewayLogin:
    # Chinese stock market trading period (day/night)
    __day_start_time = time(8, 45)
    __day_end_time = time(15, 5)

    __accounts_data_fold_path = TQZFilePathOperator.grandfather_path(
            source_path=TQZFilePathOperator.current_file_father_path(
                file=__file__
            )
        ) + f"/.vntrader/accounts_data"

    __accounts_data_jsonfile_path = __accounts_data_fold_path + "/accounts_data.json"

    def __init__(self, gateway: Type[BaseGateway], init_strategies_seconds):

        self.gateway = gateway
        self.init_strategies_seconds = init_strategies_seconds
        self.gateway_name = gateway(event_engine=None).gateway_name


    def tqz_login_accounts(self, account_app_classes: [Type[BaseApp]]):
        """
        Login all accounts in the same gateway with app_classes.
        """

        gateway_settings = self.__get_gateway_settings(gateway_name_lower=self.gateway_name.lower())
        ACCOUNT_ID = TQZStockGatewaySettingKey.ACCOUNT_ID.value

        accounts_child_process: {str: None} = {}
        for gateway_setting in gateway_settings:
            accounts_child_process[gateway_setting[ACCOUNT_ID]] = None

        while True:
            trading = self.__check_trading_period()

            for gateway_setting in gateway_settings:

                # Start child process in trading period
                if trading and accounts_child_process[gateway_setting[ACCOUNT_ID]] is None:
                    accounts_child_process[gateway_setting[ACCOUNT_ID]] = multiprocessing.Process(
                        target=self._run_account,
                        args=(gateway_setting, account_app_classes,)
                    )
                    accounts_child_process[gateway_setting[ACCOUNT_ID]].start()

                # 非记录时间则退出子进程
                if not trading and accounts_child_process[gateway_setting[ACCOUNT_ID]] is not None:
                    if not accounts_child_process[gateway_setting[ACCOUNT_ID]].is_alive():
                        accounts_child_process[gateway_setting[ACCOUNT_ID]] = None
                        print("子进程关闭成功")

                sleep(10)

    def _run_account(self, gateway_setting, account_app_classes):
        """
        Running all accounts in the same gateway.
        """

        SETTINGS["log.file"] = True

        event_engine = EventEngine()
        main_engine = MainEngine(event_engine)
        main_engine.add_gateway(gateway_class=self.gateway)

        for account_app_class in account_app_classes:
            current_engine = main_engine.add_app(account_app_class)
            main_engine.write_log(f'{current_engine}引擎 创建成功')

            log_engine = main_engine.get_engine("log")
            event_engine.register(EVENT_CTA_LOG, log_engine.process_log_event)
            main_engine.write_log("注册日志事件监听")

            main_engine.connect(gateway_setting, gateway_name=self.gateway_name)
            main_engine.write_log("连接" + self.gateway_name + "接口")

            sleep(self.init_strategies_seconds)
            current_engine.init_engine()
            main_engine.write_log(f'{current_engine.engine_name} 策略 初始化完成')

            current_engine.init_all_strategies()
            print(f'{current_engine.engine_name} strategies: ' + str(current_engine.strategies))
            sleep(self.init_strategies_seconds)
            main_engine.write_log(f'{current_engine.engine_name} 策略 全部初始化')

            # current_engine.start_all_strategies()
            # main_engine.write_log(f'{current_engine.engine_name} 策略 全部启动')
            # print("交易中")

        while True:
            sleep(10)
            trading = self.__check_trading_period()
            if not trading:
                print("关闭子进程")
                main_engine.close()
                sys.exit(0)


    # -- private part ---
    def __check_trading_period(self):
        """ """
        current_time = datetime.now().time()

        trading = False

        if self.__day_start_time <= current_time <= self.__day_end_time:
            trading = True

        return trading


    @classmethod
    def __get_gateway_settings(cls, gateway_name_lower: str):

        cls.__tqz_update_accounts_data_jsonfile()

        target_file_path = cls.__accounts_data_fold_path + f"/{gateway_name_lower.lower()}_settings.json"
        if os.path.exists(path=target_file_path):
            gateway_settings = TQZJsonOperator.tqz_load_jsonfile(jsonfile=target_file_path)
        else:
            gateway_settings = {}

        return gateway_settings

    @classmethod
    def __tqz_update_accounts_data_jsonfile(cls):
        if not os.path.exists(path=cls.__accounts_data_fold_path):
            os.makedirs(cls.__accounts_data_fold_path)
            TQZJsonOperator.tqz_write_jsonfile(content={}, target_jsonfile=cls.__accounts_data_jsonfile_path)

        # separate gateway_settings.json and others...
        all_gateway_settings_content_list = []
        current_accounts_data = {}
        for base_path, folder_list, file_list in os.walk(cls.__accounts_data_fold_path):
            for file_name in file_list:
                full_path = cls.__accounts_data_fold_path + '/' + file_name

                if file_name.split(".")[0].endswith("settings"):
                    all_gateway_settings_content_list.append(
                        TQZJsonOperator.tqz_load_jsonfile(jsonfile=full_path)
                    )
                else:
                    if os.path.exists(path=cls.__accounts_data_jsonfile_path):
                        current_accounts_data = TQZJsonOperator.tqz_load_jsonfile(jsonfile=cls.__accounts_data_jsonfile_path)

        current_source_accounts_names = []
        for gateway_settings in all_gateway_settings_content_list:
            for gateway_setting in gateway_settings:
                current_source_accounts_names.append(gateway_setting[TQZStockGatewaySettingKey.ACCOUNT_ID.value])

        should_remove_account_list = []
        for current_account in current_accounts_data.keys():
            if current_account not in current_source_accounts_names:
                should_remove_account_list.append(current_account)

        if len(should_remove_account_list) is 0:
            return
        else:
            for should_remove_account in should_remove_account_list:
                del current_accounts_data[should_remove_account]
            TQZJsonOperator.tqz_write_jsonfile(content=current_accounts_data, target_jsonfile=cls.__accounts_data_jsonfile_path)


if __name__ == "__main__":
    TQZGatewayLogin(
        gateway=XtpGateway,
        init_strategies_seconds=60
    ).tqz_login_accounts(
        account_app_classes=[CtaStrategyApp, PositionManagerApp, TQZDataDumpApp]
    )
