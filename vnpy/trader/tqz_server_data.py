import math
import pandas
import datetime

from typing import List

from tqsdk import TqApi, TqKq
from tqsdk.objs import Quote

from vnpy.trader.tqz_extern.tqz_constant import TQZCurrentFutureContractColumnType

from vnpy.trader.tqz_extern.tools.pandas_operator.pandas_operator import TQZPandas
TQZPandas.pre_set()


class TQZServerData:
    """
    """

    def __init__(self, account_name="nimahannisha", account_password="tnt19860427"):
        """
        init api with account_name & account_password
        """

        self.tq_api = TqApi(TqKq(), auth=f'{account_name},{account_password}')


    def tqz_load_current_future_contracts_dataframe(self):

        all_tq_symbols = []
        try:
            all_tq_symbols = self.tq_api.query_quotes(ins_class="FUTURE", expired=False)
        except:
            pass
        finally:
            quotes = self.tq_api.get_quote_list(symbols=all_tq_symbols)
            self.tq_api.close()

        return self.__get_current_future_contract_sedimentary_funds_dataframe(quotes=quotes)


    def tqz_load_main_contracts(self):
        """
        Load main contracts from TqSdk
        """

        main_vt_symbols = []
        try:
            tq_main_contracts = self.tq_api.query_quotes(ins_class="CONT")

            [main_vt_symbols.append(
                self.__get_vt_symbol(
                    tq_symbol=self.tq_api.get_quote(
                        symbol=main_contract
                    ).underlying_symbol
                )
            ) for main_contract in tq_main_contracts]

        except:
            pass

        finally:
            print("主力合约数据收取完成")
            print("main_vt_symbols: " + str(main_vt_symbols))
            self.tq_api.close()

        return main_vt_symbols

    @staticmethod
    def today_string():
        return str(datetime.date.today())


    # --- private part ---
    def __get_current_future_contract_sedimentary_funds_dataframe(self, quotes: List[Quote]):
        """
        Get current future_contract_sedimentary_funds_dataframe without contract which last_price is non or open_interest is 0
        """

        contracts = []
        all_close_prices = []
        open_interests = []
        contracts_multi = []
        sedimentary_funds = []

        for quote in quotes:
            if math.isnan(quote.last_price) is True or (quote.open_interest is 0):
                continue
            contracts.append(self.__get_vt_symbol(tq_symbol=quote.instrument_id))
            all_close_prices.append(quote.last_price)
            open_interests.append(quote.open_interest)
            contracts_multi.append(quote.volume_multiple)
            # 沉淀资金: 持仓量(双边) * 最新价格 * 合约乘数 * 保证金比例(默认 0.1)
            sedimentary_funds.append(int(quote.open_interest * 2 * quote.last_price * quote.volume_multiple * 0.1))

        current_future_contracts_dataframe = pandas.DataFrame({
            TQZCurrentFutureContractColumnType.CONTRACT_CODE.value: contracts,
            TQZCurrentFutureContractColumnType.CLOSE_PRICE_TODAY.value: all_close_prices,
            TQZCurrentFutureContractColumnType.OPEN_INTEREST_TODAY.value: open_interests,
            TQZCurrentFutureContractColumnType.CONTRACT_MULTI.value: contracts_multi,
            TQZCurrentFutureContractColumnType.SEDIMENTARY_FUND_TODAY.value: sedimentary_funds,
        })

        return current_future_contracts_dataframe

    @staticmethod
    def __get_vt_symbol(tq_symbol):
        """
        Change tq_symbol format to vt_symbol format
        """
        return f'{tq_symbol.split(".")[1]}.{tq_symbol.split(".")[0]}'


if __name__ == '__main__':
    TQZServerData().tqz_load_current_future_contracts_dataframe()