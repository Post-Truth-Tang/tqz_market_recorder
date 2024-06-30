
from typing import List

from vnpy.trader.object import PositionData
from vnpy.trader.constant import Direction


class TQZPositionData:

    __position_datas = None
    __position_data_models = None

    __is_refresh = False

    __vt_symbol_key = "vt_symbol"
    __direction_key = "direction"
    __lot_key = "lot"
    __yesterday_lot_key = "yesterday_lot"

    
    def __init__(self, vt_symbol_direction, vt_symbol, direction, lot, yesterday_lot):
        self.vt_symbol_direction = vt_symbol_direction
        self.vt_symbol = vt_symbol
        self.direction = direction
        self.lot = lot
        self.yesterday_lot = yesterday_lot

    @classmethod
    def is_refresh(cls):
        return cls.__is_refresh

    @classmethod
    def position_data_models(cls):

        if cls.__position_data_models is None:
            return []

        return cls.__position_data_models

    @classmethod
    def tqz_marketVtSymbol_exist_in_account(cls, market_vt_symbol):
        """
        Market_vt_symbol is exist in account or not 
        """

        is_exist = False
        for position_data in cls.position_data_models():
            if market_vt_symbol == position_data.vt_symbol:
                is_exist = True
                break

        return is_exist

    @classmethod
    def tqz_update_position_datas(cls, new_position_datas: [str, List[PositionData]]):
        """
        Refresh new position datas when real position datas is update
        """

        position_datas_dictionary = cls.__change_new_position_datas_format(
            new_position_datas=new_position_datas
        )

        cls.__is_refresh = cls.__position_datas_is_refresh(
            old_position_datas=cls.__position_datas,
            new_position_datas=position_datas_dictionary
        )

    @classmethod
    def tqz_get_yesterday_position(cls, market_vt_symbol, direction: Direction):
        """
        Get yesterday(buy, sell) position of market_vt_symbol 
        """

        lot_result = 0

        if direction == Direction.LONG:
            lot_result = cls.__get_yesterday_lot(
                vt_symbol_direction=f'{market_vt_symbol}.{str(Direction.LONG.value)}'
            )
        elif direction == Direction.SHORT:
            lot_result = cls.__get_yesterday_lot(
                vt_symbol_direction=f'{market_vt_symbol}.{str(Direction.SHORT.value)}'
            )

        return lot_result


    @classmethod
    def tqz_get_real_position(cls, market_vt_symbol, direction: Direction):
        """
        Get real(buy, sell, net) position of market_vt_symbol
        """

        lot_result = 0

        if direction == Direction.LONG:
            lot_result = cls.__get_lot(
                vt_symbol_direction=f'{market_vt_symbol}.{str(Direction.LONG.value)}'
            )
        elif direction == Direction.SHORT:
            lot_result = cls.__get_lot(
                vt_symbol_direction=f'{market_vt_symbol}.{str(Direction.SHORT.value)}'
            )
        elif direction == Direction.NET:
            temp_lot_buy = cls.__get_lot(
                vt_symbol_direction=f'{market_vt_symbol}.{str(Direction.LONG.value)}'
            )
            temp_lot_sell = cls.__get_lot(
                vt_symbol_direction=f'{market_vt_symbol}.{str(Direction.SHORT.value)}'
            )

            lot_result = temp_lot_buy + (temp_lot_sell * -1)

        return lot_result

    @classmethod
    def tqz_risk_control(cls, lot):
        """ 
        Make sure lot can't big than 99
        """

        if lot > 99:
            lot = 99
        elif lot < -99:
            lot = -99

        return abs(lot)


    # --- private part ---
    @classmethod
    def __remove_empty_positions(cls, new_position_datas):
        empty_positions = {}
        for vt_symbol_direction, position_data in new_position_datas.items():
            if position_data.volume != 0:
                empty_positions[vt_symbol_direction] = position_data

        return empty_positions


    @classmethod
    def __position_datas_is_refresh(cls, old_position_datas, new_position_datas):
        """ 
        Real position datas is refresh or not
        """

        if old_position_datas != new_position_datas:  # real position datas is change (need refresh cls.__position_datas)
            # print("real positions:" + str(new_position_datas))
            cls.__position_datas = new_position_datas

            # refresh position data models
            cls.__position_data_models = cls.__refresh_position_data_models(
                new_position_datas_dictionary=new_position_datas
            )

            is_refresh = True
        else:
            is_refresh = False

        return is_refresh

    @classmethod
    def __change_new_position_datas_format(cls, new_position_datas: [str, List[PositionData]]):
        """ 
        Change new position datas format
        """

        new_position_datas = cls.__remove_empty_positions(new_position_datas=new_position_datas)

        position_datas_dictionary = {}
        for vt_symbol_direction, position_data in new_position_datas.items():
            position_datas_dictionary[vt_symbol_direction] = {
                cls.__vt_symbol_key: position_data.vt_symbol,
                cls.__direction_key: position_data.direction,
                cls.__lot_key: position_data.volume,
                cls.__yesterday_lot_key: position_data.yd_volume
            }

        return position_datas_dictionary

    @classmethod
    def __refresh_position_data_models(cls, new_position_datas_dictionary):
        """ 
        Refresh position data models 
        """

        position_data_models = []
        for vt_symbol_direction, position_data in new_position_datas_dictionary.items():
            new_position_data_model = TQZPositionData(
                vt_symbol_direction=vt_symbol_direction,
                vt_symbol=position_data[cls.__vt_symbol_key],
                direction=position_data[cls.__direction_key],
                lot=position_data[cls.__lot_key],
                yesterday_lot=position_data[cls.__yesterday_lot_key]
            )
            position_data_models.append(new_position_data_model)

        return position_data_models

    @classmethod
    def __get_lot(cls, vt_symbol_direction):
        """ 
        Get real position(buy, sell, net) with vt_symbol_direction 
        """

        lot_result = 0
        for position_data_model in cls.position_data_models():
            if position_data_model.vt_symbol_direction == vt_symbol_direction:
                lot_result = position_data_model.lot
                break
            else:
                lot_result = 0

        return lot_result

    @classmethod
    def __get_yesterday_lot(cls, vt_symbol_direction):
        """ 
        Get yesterday position(buy, sell) with vt_symbol_direction 
        """

        yesterday_lot_result = 0
        for position_data_model in cls.position_data_models():
            if position_data_model.vt_symbol_direction == vt_symbol_direction:
                yesterday_lot_result = position_data_model.yesterday_lot
                break
            else:
                yesterday_lot_result = 0

        return yesterday_lot_result
