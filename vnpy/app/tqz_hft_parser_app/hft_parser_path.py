
import os
from datetime import datetime

from vnpy.trader.tqz_extern.tools.file_path_operator.file_path_operator import TQZFilePathOperator

class TQZHftParserPath:

    # --- hft merits part ---
    @classmethod
    def hft_merits_fold(cls):
        all_path = f'{cls.__parser_result_fold()}/hft_merits_fold'

        if os.path.exists(all_path) is False:
            os.mkdir(all_path)

        return all_path


    # --- trade part ---
    @classmethod
    def trade_source_log_allPath(cls):
        all_path = f'{cls.__source_log_fold()}/hft_tradeChange_{datetime.now().strftime("%Y%m%d")}.log'

        assert os.path.exists(all_path), f'{all_path} not exist'
        return all_path

    @classmethod
    def parser_trade_result_fold(cls):
        parser_trade_result_fold = f'{cls.__parser_result_fold()}/{"parser_trade_result_" + datetime.now().strftime("%Y%m%d")}'

        if os.path.exists(parser_trade_result_fold) is False:
            os.mkdir(parser_trade_result_fold)

        return parser_trade_result_fold


    # --- order part ---
    @classmethod
    def order_source_log_allPath(cls):
        all_path = f'{cls.__source_log_fold()}/hft_cancelOrderCounts_{datetime.now().strftime("%Y%m%d")}.log'

        assert os.path.exists(all_path), f'{all_path} not exist'
        return all_path

    @classmethod
    def code_cancelOrderCounts_json_allPath(cls):
        return f'{cls.parser_order_result_fold()}/code_cancelOrderCounts.json'

    @classmethod
    def parser_order_result_fold(cls):
        parser_order_result_fold = f'{cls.__parser_result_fold()}/{"parser_order_result_" + datetime.now().strftime("%Y%m%d")}'

        if os.path.exists(parser_order_result_fold) is False:
            os.mkdir(parser_order_result_fold)

        return parser_order_result_fold


    # --- private part ---
    @staticmethod
    def __parser_result_fold():
        return f'{TQZFilePathOperator.father_path(source_path=__file__)}/parser_result_fold'

    @staticmethod
    def __source_log_fold():
        return f'{TQZFilePathOperator.father_path(source_path=__file__)}/source_log_fold'


if __name__ == '__main__':
    pass