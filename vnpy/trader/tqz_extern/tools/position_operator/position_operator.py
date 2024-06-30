import json
import math
import re

from vnpy.trader.tqz_extern.tqz_constant import (
    TQZCffexSymbolType,
    TQZJsonOperatorType,
    TQZCodingType,
    TQZPositionKeyType
)

class TQZJsonOperator:

    @classmethod
    def tqz_load_jsonfile(cls, jsonfile=None):
        """
        Load json file content
        """

        if jsonfile is None:
            raise Exception("Error: filename is None")
        else:
            try:
                return cls.__writeReadFile_except_throw(jsonfile=jsonfile, operation_type=TQZJsonOperatorType.READ_TYPE)
            except Exception:
                return None

    @classmethod
    def tqz_write_jsonfile(cls, content=None, target_jsonfile=None):
        """
        Write content to target json file
        """

        if target_jsonfile is None:
            raise Exception("Error: target_jsonfile is None")
        else:
            try:
                cls.__writeReadFile_except_throw(jsonfile=target_jsonfile, content=content, operation_type=TQZJsonOperatorType.WRITE_TYPE)
            except Exception as result:
                raise Exception(result)
                pass


    @classmethod
    def __writeReadFile_except_throw(cls, jsonfile=None, content=None, operation_type=TQZJsonOperatorType.READ_TYPE):
        if operation_type is TQZJsonOperatorType.READ_TYPE:

            try:
                with open(jsonfile, operation_type.value, encoding=TQZCodingType.UTF_8_CODING.value) as fp:
                    return json.load(fp=fp)
            except json.decoder.JSONDecodeError:
                raise Exception("json content is error")
            except Exception:
                raise Exception("unknow error: __writeReadFile_except_operation")

        elif operation_type is TQZJsonOperatorType.WRITE_TYPE:

            content_type = type(content)
            if content_type != dict and content_type != str and content_type != list:
                raise Exception("type of content is error")
            else:
                with open(jsonfile, operation_type.value, encoding=TQZCodingType.UTF_8_CODING.value) as fp:
                    json.dump(content, fp=fp, ensure_ascii=False, indent=4)


class TQZPositionJsonOperator(TQZJsonOperator):

    @classmethod
    def tqz_get_single_jsonfile_format_data(cls, jsonfile=None):
        """
        Get single json file content have position datas(buy, sell, net)
        """

        content_dictionary = cls.tqz_load_jsonfile(jsonfile=jsonfile)

        empty_content_dictionary = {}
        for vt_symbol_strategy, data in content_dictionary.items():
            for position_key, position_data in data.items():
                if position_key == TQZPositionKeyType.POSITION_KEY.value:
                    if position_data > 0:
                        buy_position, sell_position, net_position = abs(position_data), 0, position_data
                    else:
                        buy_position, sell_position, net_position = 0, abs(position_data), position_data

                    empty_content_dictionary[vt_symbol_strategy] = {
                        TQZPositionKeyType.BUY_POSITION_KEY.value: buy_position,
                        TQZPositionKeyType.SELL_POSITION_KEY.value: sell_position,
                        TQZPositionKeyType.NET_POSITION_KEY.value: net_position
                    }

        return empty_content_dictionary

    @classmethod
    def tqz_get_sum_position_format_data(cls, *jsonfile_list):
        """
        Get sum of all position datas(buy, sell, net)
        """

        jsonfile_list_without_null = []
        for jsonfile in jsonfile_list:
            if jsonfile not in [None, {}]:
                jsonfile_list_without_null.append(jsonfile)

        jsonfile_content_list = []
        [jsonfile_content_list.append(cls.tqz_get_single_jsonfile_format_data(jsonfile)) for jsonfile in jsonfile_list_without_null]

        return cls.tqz_get_sum_position_format_data_with_jsonfileContentList(
            *jsonfile_content_list
        )


    @classmethod
    def tqz_get_multi_format_data(cls, format_content, multi=1):
        """
        Get all positions of format_content with multi times:
        1. multi > 0: change position to multi times;
        2. multi = 0: change position to min according to current direction;
        3. multi < 0: exchange buy/sell position to multi sell/buy position;
        """

        if multi >= 0:
            format_content = cls.__get_plus_multi_format_data(format_content=format_content, multi=multi)
        else:
            format_content = cls.__get_minus_multi_format_data_exchange(format_content=format_content, multi=multi)

        return format_content

    @classmethod
    def tqz_get_empty_format_data(cls, format_content):
        """
        Clear all position(buy, sell, net) of format_content
        """

        # remove stock index
        sum_content_remove_stock_index = {}
        for strategy_symbol, data in format_content.items():
            stock_index = re.match(r"^[a-zA-Z]{1,3}", strategy_symbol).group()

            if stock_index not in [TQZCffexSymbolType.IC.value, TQZCffexSymbolType.IF.value, TQZCffexSymbolType.IH.value]:
                sum_content_remove_stock_index[strategy_symbol] = data

        for vt_symbol, data in sum_content_remove_stock_index.items():
            data[TQZPositionKeyType.BUY_POSITION_KEY.value], data[TQZPositionKeyType.SELL_POSITION_KEY.value], data[TQZPositionKeyType.NET_POSITION_KEY.value] = 0, 0, 0

            sum_content_remove_stock_index[vt_symbol] = data

        return sum_content_remove_stock_index


    @classmethod
    def tqz_get_ER_position_format_data(cls, jsonfile):
        """
        Get ER position format data with jsonfile
        """

        if jsonfile in [None, {}]:
            return {}

        er_content_data = cls.tqz_load_jsonfile(jsonfile=jsonfile)

        empty_content_dictionary = {}
        for main_data in er_content_data.values():
            for target_position_key, position_datas in main_data.items():
                if target_position_key == TQZPositionKeyType.TARGET_POSITION_ER_KEY.value:
                    for vt_symbol, position_data in position_datas.items():
                        if position_data > 0:
                            buy_position, sell_position, net_position = abs(position_data), 0, position_data
                        else:
                            buy_position, sell_position, net_position = 0, abs(position_data), position_data

                        if vt_symbol in empty_content_dictionary.keys():
                            buy_position += empty_content_dictionary[vt_symbol][TQZPositionKeyType.BUY_POSITION_KEY.value]
                            sell_position += empty_content_dictionary[vt_symbol][TQZPositionKeyType.SELL_POSITION_KEY.value]
                            net_position += empty_content_dictionary[vt_symbol][TQZPositionKeyType.NET_POSITION_KEY.value]

                        empty_content_dictionary[vt_symbol] = {
                            TQZPositionKeyType.BUY_POSITION_KEY.value: buy_position,
                            TQZPositionKeyType.SELL_POSITION_KEY.value: sell_position,
                            TQZPositionKeyType.NET_POSITION_KEY.value: net_position
                        }

        return empty_content_dictionary

    @classmethod
    def tqz_get_sum_position_format_data_with_jsonfileContentList(cls, *jsonfile_content_list):
        """
        Get sum of all position datas(buy, sell, net) use sum data of all jsonfile contents
        """

        temp_dic_list = []
        for single_json_content in jsonfile_content_list:
            if single_json_content in [None, {}]:
                continue
            temp_dic = {}
            for key, value in single_json_content.items():
                vt_symbol = key.split(".")[0] + "." + key.split(".")[1]
                temp_dic[vt_symbol] = value
            temp_dic_list.append(temp_dic)
        dic_list = temp_dic_list

        sum_content = {}
        for jsonfile_content in dic_list:
            for vt_symbol, data in jsonfile_content.items():
                if vt_symbol in sum_content.keys():
                    sum_content[vt_symbol][TQZPositionKeyType.BUY_POSITION_KEY.value] += data[TQZPositionKeyType.BUY_POSITION_KEY.value]
                    sum_content[vt_symbol][TQZPositionKeyType.SELL_POSITION_KEY.value] += data[TQZPositionKeyType.SELL_POSITION_KEY.value]
                    sum_content[vt_symbol][TQZPositionKeyType.NET_POSITION_KEY.value] += data[TQZPositionKeyType.NET_POSITION_KEY.value]
                else:
                    sum_content[vt_symbol] = {
                        TQZPositionKeyType.BUY_POSITION_KEY.value: data[TQZPositionKeyType.BUY_POSITION_KEY.value],
                        TQZPositionKeyType.SELL_POSITION_KEY.value: data[TQZPositionKeyType.SELL_POSITION_KEY.value],
                        TQZPositionKeyType.NET_POSITION_KEY.value: data[TQZPositionKeyType.NET_POSITION_KEY.value]
                    }

        return sum_content



    # --- private part ---
    @classmethod
    def __get_plus_multi_format_data(cls, format_content, multi=1):

        for vt_symbol, data in format_content.items():

            before_buy_position, before_sell_position, before_net_position = data[TQZPositionKeyType.BUY_POSITION_KEY.value], data[TQZPositionKeyType.SELL_POSITION_KEY.value], data[TQZPositionKeyType.NET_POSITION_KEY.value]

            data[
                TQZPositionKeyType.BUY_POSITION_KEY.value
            ], data[
                TQZPositionKeyType.SELL_POSITION_KEY.value
            ] = math.floor(
                before_buy_position * multi
            ), math.floor(
                before_sell_position * multi
            )

            if before_net_position > 0:
                data[TQZPositionKeyType.NET_POSITION_KEY.value] = math.floor(before_net_position * multi)
            else:
                data[TQZPositionKeyType.NET_POSITION_KEY.value] = math.ceil(before_net_position * multi)

            if before_net_position > 0 and data[TQZPositionKeyType.NET_POSITION_KEY.value] is 0:
                data[TQZPositionKeyType.BUY_POSITION_KEY.value], data[TQZPositionKeyType.NET_POSITION_KEY.value] = 1, 1
            elif before_net_position < 0 and data[TQZPositionKeyType.NET_POSITION_KEY.value] is 0:
                data[TQZPositionKeyType.SELL_POSITION_KEY.value], data[
                    TQZPositionKeyType.NET_POSITION_KEY.value] = 1, -1

            format_content[vt_symbol] = data

        return format_content

    @classmethod
    def __get_minus_multi_format_data_exchange(cls, format_content, multi=1):

        for vt_symbol, data in format_content.items():
            buy_position, sell_position = data[TQZPositionKeyType.BUY_POSITION_KEY.value], data[
                TQZPositionKeyType.SELL_POSITION_KEY.value]

            data[
                TQZPositionKeyType.BUY_POSITION_KEY.value
            ], data[
                TQZPositionKeyType.SELL_POSITION_KEY.value
            ] = math.floor(
                sell_position * abs(multi)
            ), math.floor(
                buy_position * abs(multi)
            )

            data[TQZPositionKeyType.NET_POSITION_KEY.value] = data[TQZPositionKeyType.BUY_POSITION_KEY.value] + data[TQZPositionKeyType.SELL_POSITION_KEY.value] * (-1)

            format_content[vt_symbol] = data

        return format_content


def __main_engine():
    hla = "cta_strategy_datahla.json"
    hsr = "cta_strategy_datahsr.json"

    er_jsonfile = "portfolio_strategy_data.json"
    cta_content = TQZPositionJsonOperator.tqz_get_sum_position_format_data(hla, hsr)
    er_content = TQZPositionJsonOperator.tqz_get_ER_position_format_data(jsonfile=er_jsonfile)

    sum_content = TQZPositionJsonOperator.tqz_get_sum_position_format_data_with_jsonfileContentList(cta_content, er_content)

    TQZJsonOperator.tqz_write_jsonfile(content=sum_content, target_jsonfile="sum_ZSTZ2.json")


if __name__ == '__main__':
    __main_engine()
