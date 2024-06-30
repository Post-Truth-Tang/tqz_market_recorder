import os

from vnpy.app.tqz_hft_parser_app.hft_parser_path import TQZHftParserPath

from vnpy.trader.tqz_extern.tools.position_operator.position_operator import TQZJsonOperator
from vnpy.trader.tqz_extern.tools.pandas_operator.pandas_operator import pandas

from vnpy.app.tqz_hft_parser_app.tqz_constant import TQZTradeLogTitles, TQZOrderType, TQZHftSheetType, TQZHftMeritsTitles

class TQZHftMerits:

    # --- api part ---
    @classmethod
    def tqz_create(cls, parser_trade_result_fold, code_cancelOrderCounts_json_allPath, hft_merits_fold):
        """
        create hft merits of every code.
        """
        for file_name in os.listdir(hft_merits_fold):
            os.remove(path=hft_merits_fold + f'/{file_name}')

        for parser_trade_result_code_file in os.listdir(parser_trade_result_fold):
            all_path = f'{parser_trade_result_fold}/{parser_trade_result_code_file}'
            code_cancelOrderTimes_dictionary = TQZJsonOperator.tqz_load_jsonfile(jsonfile=code_cancelOrderCounts_json_allPath)
            code_csv_content = pandas.read_csv(all_path)

            code_merits_detailed_dataframe = cls.__get_code_merits_detailed_dataframe(code_csv_content=code_csv_content)

            # cancel_order_limits
            source_code_name = parser_trade_result_code_file.split('.')[0]
            code_name = source_code_name.replace('_', '.')
            if code_name in code_cancelOrderTimes_dictionary.keys():
                cancel_order_limits = code_cancelOrderTimes_dictionary[code_name]
            else:
                cancel_order_limits = 0

            code_merits_total_dataframe = cls.__get_code_merits_total_dataframe(
                sum_slippage=code_merits_detailed_dataframe[TQZTradeLogTitles.SLIPPAGE.value].sum(),
                cancel_order_limits=cancel_order_limits,
                trade_times=len(code_merits_detailed_dataframe),
                send_order_times=len(code_merits_detailed_dataframe) + int(cancel_order_limits),
                profit_and_loss_sum=cls.__get_profit_and_loss_sum(code_csv_content=code_csv_content, close_price=0)
            )

            excel_writer = pandas.ExcelWriter(path=f'{hft_merits_fold}/{source_code_name}.xlsx')
            code_merits_total_dataframe.to_excel(excel_writer, sheet_name=TQZHftSheetType.TOTAL.value, index=False, freeze_panes=(1, 0))
            code_merits_detailed_dataframe.to_excel(excel_writer, sheet_name=TQZHftSheetType.DETAILED.value, index=False, freeze_panes=(1, 0))
            excel_writer.save()


    # --- private part ---
    @staticmethod
    def __get_profit_and_loss_sum(code_csv_content, close_price):

        order_type = TQZTradeLogTitles.ORDER_TYPE.value
        receive_trade_price = TQZTradeLogTitles.RECEIVE_TRADE_PRICE.value
        lots = TQZTradeLogTitles.LOTS.value

        receive_buy_trade_price = close_price - code_csv_content.loc[code_csv_content[order_type] == TQZOrderType.BUY_ORDER_TYPE.value][receive_trade_price]
        receive_sell_trade_price = code_csv_content.loc[code_csv_content[order_type] == TQZOrderType.SELL_ORDER_TYPE.value][receive_trade_price] - close_price
        receive_short_trade_price = code_csv_content.loc[code_csv_content[order_type] == TQZOrderType.SHORT_ORDER_TYPE.value][receive_trade_price] - close_price
        receive_cover_trade_price = close_price - code_csv_content.loc[code_csv_content[order_type] == TQZOrderType.COVER_ORDER_TYPE.value][receive_trade_price]

        buy_profit_and_loss = receive_buy_trade_price * code_csv_content.loc[code_csv_content[order_type] == TQZOrderType.BUY_ORDER_TYPE.value][lots]
        sell_profit_and_loss = receive_sell_trade_price * code_csv_content.loc[code_csv_content[order_type] == TQZOrderType.SELL_ORDER_TYPE.value][lots]
        short_profit_and_loss = receive_short_trade_price * code_csv_content.loc[code_csv_content[order_type] == TQZOrderType.SHORT_ORDER_TYPE.value][lots]
        cover_profit_and_loss = receive_cover_trade_price * code_csv_content.loc[code_csv_content[order_type] == TQZOrderType.COVER_ORDER_TYPE.value][lots]

        return (buy_profit_and_loss.sum() + sell_profit_and_loss.sum() + short_profit_and_loss.sum() + cover_profit_and_loss.sum()) * code_csv_content[TQZTradeLogTitles.VOL_SCALE.value].mean()

    @staticmethod
    def __get_code_merits_detailed_dataframe(code_csv_content):
        code_merits_detailed_dataframe = pandas.DataFrame()
        code_merits_detailed_dataframe[TQZTradeLogTitles.CODE.value] = code_csv_content[TQZTradeLogTitles.CODE.value]
        code_merits_detailed_dataframe[TQZTradeLogTitles.ORDER_TYPE.value] = code_csv_content[TQZTradeLogTitles.ORDER_TYPE.value]
        code_merits_detailed_dataframe[TQZTradeLogTitles.MARKET_TIME_OF_SEND_ORDER.value] = code_csv_content[TQZTradeLogTitles.MARKET_TIME_OF_SEND_ORDER.value]
        code_merits_detailed_dataframe[TQZTradeLogTitles.SEND_ORDER_TIME.value] = code_csv_content[TQZTradeLogTitles.SEND_ORDER_TIME.value]
        code_merits_detailed_dataframe[TQZTradeLogTitles.SLIPPAGE.value] = code_csv_content[TQZTradeLogTitles.RECEIVE_TRADE_PRICE.value] - code_csv_content[TQZTradeLogTitles.SEND_ORDER_PRICE.value]
        code_merits_detailed_dataframe[TQZTradeLogTitles.RECEIVE_TRADE_TIME.value] = code_csv_content[TQZTradeLogTitles.RECEIVE_TRADE_TIME.value]

        return code_merits_detailed_dataframe

    @staticmethod
    def __get_code_merits_total_dataframe(sum_slippage, cancel_order_limits, trade_times, send_order_times, profit_and_loss_sum):
        columns = [
            TQZHftMeritsTitles.SUM_SLIPPAGE.value,
            TQZHftMeritsTitles.CANCEL_ORDER_COUNTS.value,
            TQZHftMeritsTitles.TRADE_TIMES.value,
            TQZHftMeritsTitles.SEND_ORDER_TIMES.value,
            TQZHftMeritsTitles.PROFIT_AND_LOSS.value
        ]
        code_merits_total_dataframe = pandas.DataFrame(columns=columns)
        last_line = len(code_merits_total_dataframe)

        code_merits_total_dataframe.loc[last_line, TQZHftMeritsTitles.SUM_SLIPPAGE.value] = sum_slippage
        code_merits_total_dataframe.loc[last_line, TQZHftMeritsTitles.CANCEL_ORDER_COUNTS.value] = cancel_order_limits
        code_merits_total_dataframe.loc[last_line, TQZHftMeritsTitles.TRADE_TIMES.value] = trade_times
        code_merits_total_dataframe.loc[last_line, TQZHftMeritsTitles.SEND_ORDER_TIMES.value] = send_order_times
        code_merits_total_dataframe.loc[last_line, TQZHftMeritsTitles.PROFIT_AND_LOSS.value] = profit_and_loss_sum

        return code_merits_total_dataframe


if __name__ == '__main__':
    TQZHftMerits.tqz_create(
        parser_trade_result_fold=TQZHftParserPath.parser_trade_result_fold(),
        code_cancelOrderCounts_json_allPath=TQZHftParserPath.code_cancelOrderCounts_json_allPath(),
        hft_merits_fold=TQZHftParserPath.hft_merits_fold()
    )