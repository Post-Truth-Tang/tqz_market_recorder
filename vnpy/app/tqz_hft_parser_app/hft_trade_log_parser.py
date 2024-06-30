from vnpy.trader.tqz_extern.tools.pandas_operator.pandas_operator import pandas

from vnpy.app.tqz_hft_parser_app.hft_parser_path import TQZHftParserPath
from vnpy.app.tqz_hft_parser_app.tqz_constant import TQZTradeLogTitles

class TQZHftTradeLogParser:

    @classmethod
    def tqz_start_parser(cls, trade_source_log_allPath, parser_trade_result_fold):
        trade_log_dataframe = cls.__get_source_log_dataframe(trade_source_log_allPath)

        [pandas.DataFrame.to_csv(
            cls.__get_code_log_dataframe(source_log_all_path=trade_source_log_allPath, code=code),
            path_or_buf=f'{parser_trade_result_fold}/{code.replace(".", "_")}.csv',
            index=False
        ) for code in cls.__get_all_codes(trade_log_dataframe)]


    # --- private part ---
    @classmethod
    def __get_code_log_dataframe(cls, source_log_all_path: str, code: str):
        """
        Get code dataframe based on source log with source_log_all_path and code_name.
        """
        source_log_dataframe = cls.__get_source_log_dataframe(source_log_all_path=source_log_all_path)

        return source_log_dataframe.loc[source_log_dataframe[TQZTradeLogTitles.CODE.value] == code]

    @staticmethod
    def __get_all_codes(source_log_dataframe: pandas.DataFrame) -> list:
        """
        Get codes list based on source log.
        """
        return list(set(list(source_log_dataframe[TQZTradeLogTitles.CODE.value])))

    @classmethod
    def __get_source_log_dataframe(cls, source_log_all_path: str):
        """
        Get dataframe based on source log with source_log_all_path.
        """

        line_log_dictionary_list = []
        for line in open(source_log_all_path).readlines():
            line_log_dictionary = {}
            for line_log_item in line.rstrip().split(" ")[-1].replace('[', '').replace(']', '').split(","):
                line_log_dictionary[line_log_item.split('|')[0]] = line_log_item.split('|')[1]
            line_log_dictionary_list.append(line_log_dictionary)

        return pandas.DataFrame(line_log_dictionary_list)


if __name__ == '__main__':
    TQZHftTradeLogParser.tqz_start_parser(
        trade_source_log_allPath=TQZHftParserPath.trade_source_log_allPath(),
        parser_trade_result_fold=TQZHftParserPath.parser_trade_result_fold()
    )