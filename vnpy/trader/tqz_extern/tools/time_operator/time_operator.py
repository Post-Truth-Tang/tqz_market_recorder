
from datetime import time


class TQZTimeOperator:

    @staticmethod
    def data_should_dump(now_time_second, interval_second):
        return now_time_second % interval_second is 0

    @classmethod
    def __is_commodity_morning_prohibit_time(cls, current_time, delay_minite) -> bool:
        commodity_morning_prohibit_time_start = time(9, 0)
        commodity_morning_prohibit_time_end = time(9, commodity_morning_prohibit_time_start.minute + delay_minite)

        return commodity_morning_prohibit_time_start <= current_time < commodity_morning_prohibit_time_end

    @classmethod
    def __is_commodity_night_prohibit_time(cls, current_time, delay_minute) -> bool:
        commodity_night_prohibit_time_start = time(21, 0)
        commodity_night_prohibit_time_end = time(21, commodity_night_prohibit_time_start.minute + delay_minute)

        return commodity_night_prohibit_time_start <= current_time < commodity_night_prohibit_time_end

    @classmethod
    def __is_stock_index_morning_prohibit_time(cls, current_time, delay_minute) -> bool:
        stock_index_morning_prohibit_time_start = time(9, 30)
        stock_index_morning_prohibit_time_end = time(9, stock_index_morning_prohibit_time_start.minute + delay_minute)

        return stock_index_morning_prohibit_time_start <= current_time < stock_index_morning_prohibit_time_end

    @classmethod
    def is_prohibit_time(cls, current_time, delay_minute):
        return (
            cls.__is_commodity_morning_prohibit_time(current_time=current_time, delay_minite=delay_minute) or
            cls.__is_commodity_night_prohibit_time(current_time=current_time, delay_minute=delay_minute) or
            cls.__is_stock_index_morning_prohibit_time(current_time=current_time, delay_minute=delay_minute)
        )


def __time_test():
    time1 = time(8, 59)
    time2 = time(9, 4)
    time3 = time(9, 5)

    print("TQZTimeOperator.is_prohibit_time(current_time=time1): " + str(TQZTimeOperator.is_prohibit_time(current_time=time1, delay_minute=5)))
    print("TQZTimeOperator.is_prohibit_time(current_time=time2): " + str(TQZTimeOperator.is_prohibit_time(current_time=time2, delay_minute=5)))
    print("TQZTimeOperator.is_prohibit_time(current_time=time3): " + str(TQZTimeOperator.is_prohibit_time(current_time=time3, delay_minute=5)))


if __name__ == '__main__':
    __time_test()