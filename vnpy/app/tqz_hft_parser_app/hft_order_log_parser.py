
from vnpy.trader.tqz_extern.tools.position_operator.position_operator import TQZJsonOperator

from vnpy.app.tqz_hft_parser_app.hft_parser_path import TQZHftParserPath
from vnpy.app.tqz_hft_parser_app.tqz_constant import TQZOrderLogTitles

class TQZHftOrderLogParser:
    @classmethod
    def tqz_start_parser(cls, order_source_log_allPath, code_cancelOrderCounts_json_allPath):
        TQZJsonOperator.tqz_write_jsonfile(
            content=cls.__get_source_log_dictionary(order_source_log_allPath),
            target_jsonfile=code_cancelOrderCounts_json_allPath
        )

    @classmethod
    def __get_source_log_dictionary(cls, source_log_all_path: str):
        """
        Get dictionary based on source log with source_log_all_path.
        """

        log_dictionary = {}
        for line in open(source_log_all_path).readlines():
            line_log_dictionary = {}
            for line_log_item in line.rstrip().split(" ")[-1].replace('[', '').replace(']', '').split(","):
                line_log_dictionary[line_log_item.split('|')[0]] = line_log_item.split('|')[1]
            log_dictionary[line_log_dictionary[TQZOrderLogTitles.CODE.value]] = line_log_dictionary[TQZOrderLogTitles.CANCEL_ORDER_COUNTS.value]

        return log_dictionary


if __name__ == '__main__':
    TQZHftOrderLogParser.tqz_start_parser(
        TQZHftParserPath.order_source_log_allPath(),
        TQZHftParserPath.code_cancelOrderCounts_json_allPath()
    )