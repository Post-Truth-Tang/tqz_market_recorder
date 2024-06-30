from vnpy.app.tqz_hft_parser_app.hft_parser_path import TQZHftParserPath

from vnpy.app.tqz_hft_parser_app.hft_trade_log_parser import TQZHftTradeLogParser
from vnpy.app.tqz_hft_parser_app.hft_order_log_parser import TQZHftOrderLogParser
from vnpy.app.tqz_hft_parser_app.hft_merits_creat import TQZHftMerits


class TQZHftParserKit:

    # --- api part ---
    @classmethod
    def parser_today(cls):
        cls.__reDump_parser_result()
        cls.__create_hft_merits()

    @classmethod
    def __reDump_parser_result(cls):
        """
        Parse trade & order_cancel_limits result.
        """

        TQZHftOrderLogParser.tqz_start_parser(
            order_source_log_allPath=TQZHftParserPath.order_source_log_allPath(),
            code_cancelOrderCounts_json_allPath=TQZHftParserPath.code_cancelOrderCounts_json_allPath()
        )
        TQZHftTradeLogParser.tqz_start_parser(
            trade_source_log_allPath=TQZHftParserPath.trade_source_log_allPath(),
            parser_trade_result_fold=TQZHftParserPath.parser_trade_result_fold()
        )

    @classmethod
    def __create_hft_merits(cls):
        TQZHftMerits.tqz_create(
            parser_trade_result_fold=TQZHftParserPath.parser_trade_result_fold(),
            code_cancelOrderCounts_json_allPath=TQZHftParserPath.code_cancelOrderCounts_json_allPath(),
            hft_merits_fold=TQZHftParserPath.hft_merits_fold()
        )


if __name__ == '__main__':
    TQZHftParserKit.parser_today()