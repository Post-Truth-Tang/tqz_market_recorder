
from vnpy.trader.tqz_extern.tqz_constant import (
    TQZPositionKeyType,
    TQZAccountKeyType,
    TQZAccountNameType
)

from datetime import datetime, time

from vnpy.trader.tqz_extern.tools.file_path_operator.file_path_operator import TQZFilePathOperator
from vnpy.trader.tqz_extern.tools.position_operator.position_operator import TQZJsonOperator


class TQZPositionModel:

    def __init__(self, position_dictionary):
        if TQZPositionKeyType.POSITION_KEY.value in position_dictionary.keys():
            self.lots = position_dictionary[TQZPositionKeyType.POSITION_KEY.value]
        else:
            self.lots = None

        if TQZPositionKeyType.ENTRYPRICE_KEY.value in position_dictionary.keys():
            self.entry_price = position_dictionary[TQZPositionKeyType.ENTRYPRICE_KEY.value]
        else:
            self.entry_price = None

        if TQZPositionKeyType.TARGET_POSITION_KEY.value in position_dictionary.keys():
            self.target_position = position_dictionary[TQZPositionKeyType.TARGET_POSITION_KEY.value]
        else:
            self.target_position = None

    def model_to_dictionary(self):
        empty_dictionary = {}

        if self.lots is not None:
            empty_dictionary[TQZPositionKeyType.POSITION_KEY.value] = self.lots

        if self.entry_price is not None:
            empty_dictionary[TQZPositionKeyType.ENTRYPRICE_KEY.value] = self.entry_price

        if self.target_position is not None:
            empty_dictionary[TQZPositionKeyType.TARGET_POSITION_KEY.value] = self.target_position

        return empty_dictionary


class TQZContractModel:
    def __init__(self, contract_name, position_model):
        self.name = contract_name
        self.__position_model = position_model

    @property
    def position_model(self):
        return self.__position_model

    @position_model.setter
    def position_model(self, position_model):
        self.__position_model = position_model

    @position_model.getter
    def position_model(self):
        return self.__position_model

    @classmethod
    def dictionary_to_models(cls, data_dictionary):
        contract_models = []
        for contract_name, position_dictionary in data_dictionary.items():
            contract_model = TQZContractModel(
                contract_name=contract_name,
                position_model=TQZPositionModel(position_dictionary=position_dictionary)
            )
            contract_models.append(contract_model)
        return contract_models

    @classmethod
    def models_to_dictionary(cls, *models):
        empty_dictionary = {}
        for model in models:
            empty_dictionary[model.name] = model.position_model.model_to_dictionary()
        return empty_dictionary


class TQZMonitorTimeModel:
    """
    Monitor time of main_contracts_load、yesterday_accounts_data、auto_report、main_contract_change
    """

    MAIN_CONTRACT_LOAD_START_TIME = time(15, 20)
    MAIN_CONTRACT_LOAD_END_TIME = time(15, 30)

    RECORD_YESTERDAY_DATA_START_TIME = time(15, 30)
    RECORD_YESTERDAY_DATA_END_TIME = time(15, 35)

    SEDIMENTARY_FUND_LOAD_START_TIME = time(15, 35)
    SEDIMENTARY_FUND_LOAD_END_TIME = time(15, 45)

    AUTO_REPORT_START_TIME = time(15, 45)
    AUTO_REPORT_END_TIME = time(20, 15)

    MAIN_CONTRACT_CHANGE_START_TIME = time(20, 20)
    MAIN_CONTRACT_CHANGE_END_TIME = time(20, 30)

    @classmethod
    def current_time(cls):
        return datetime.now().time()

    @classmethod
    def is_load_main_contracts_time(cls):
        start_time = cls.MAIN_CONTRACT_LOAD_START_TIME
        end_time = cls.MAIN_CONTRACT_LOAD_END_TIME
        return start_time <= cls.current_time() <= end_time

    @classmethod
    def is_record_settlement_jsonfile_time(cls):
        start_time = cls.RECORD_YESTERDAY_DATA_START_TIME
        end_time = cls.RECORD_YESTERDAY_DATA_END_TIME
        return start_time <= cls.current_time() <= end_time

    @classmethod
    def is_load_sedimentary_fund_time(cls):
        start_time = cls.SEDIMENTARY_FUND_LOAD_START_TIME
        end_time = cls.SEDIMENTARY_FUND_LOAD_END_TIME
        return start_time <= cls.current_time() <= end_time

    @classmethod
    def is_auto_report_time(cls):
        start_time = cls.AUTO_REPORT_START_TIME
        end_time = cls.AUTO_REPORT_END_TIME
        return start_time <= cls.current_time() <= end_time

    @classmethod
    def is_change_main_contracts_time(cls):
        start_time = cls.MAIN_CONTRACT_CHANGE_START_TIME
        end_time = cls.MAIN_CONTRACT_CHANGE_END_TIME
        return start_time <= cls.current_time() <= end_time


class TQZAccountModel:

    def __init__(self, account_id, balance, risk_percent, yesterday_accounts_data=None):

        if yesterday_accounts_data is None:
            yesterday_accounts_data = {}

        self.account_id = account_id
        self.account_name = self.__all_accountId_name_setting(account_id=self.account_id)

        self.balance = round(float(balance), 2)
        self.risk_percent = round(float(risk_percent), 2)

        if self.account_id in yesterday_accounts_data.keys():
            self.__yesterday_balance = round(float(yesterday_accounts_data[self.account_id][TQZAccountKeyType.BALANCE_KEY.value]), 2)
        else:
            self.__yesterday_balance = self.balance

        self.profit_and_loss = round(self.balance - self.__yesterday_balance, 2)

        self.used_deposit = round(balance * (risk_percent * 0.01), 2)
        self.available = round(balance - self.used_deposit, 2)


    def __repr__(self):
        return repr((self.account_id, self.balance, self.risk_percent, self.profit_and_loss))

    @classmethod
    def list_to_models(cls, account_data_list, yesterday_accounts_data=None):
        account_models = []
        for account_data in account_data_list:
            account_model = TQZAccountModel(
                account_id=account_data[TQZAccountKeyType.ACCOUNT_ID_KEY.value],
                balance=account_data[TQZAccountKeyType.BALANCE_KEY.value],
                risk_percent=account_data[TQZAccountKeyType.RISK_PERCENT_KEY.value],
                yesterday_accounts_data=yesterday_accounts_data
            )
            account_models.append(account_model)

        return account_models


    # --- private part ---
    @staticmethod
    def __all_accountId_name_setting(account_id: str):

        accounts_name_setting_path = TQZFilePathOperator.current_file_grandfather_path(
            file=TQZFilePathOperator.grandfather_path(source_path=__file__)
        ) + '/.vntrader/accounts_name_setting.json'
        accounts_name_setting_content = TQZJsonOperator.tqz_load_jsonfile(jsonfile=accounts_name_setting_path)

        if account_id in accounts_name_setting_content.keys():
            account_name = accounts_name_setting_content[account_id][TQZAccountNameType.WEB_NAME.value]
        else:
            account_name = "XXXX"

        return account_name
