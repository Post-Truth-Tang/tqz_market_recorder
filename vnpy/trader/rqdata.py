import pandas as pd
from tqsdk import TqApi
from datetime import timedelta
from typing import List, Optional

from .setting import SETTINGS
from .constant import Exchange, Interval
from .object import BarData, HistoryRequest
from tqsdk import TqApi, TqKq

# 时间戳对齐
TIME_GAP = 8 * 60 * 60 * 1000000000
INTERVAL_VT2TQ = {
    Interval.MINUTE: 60,
    Interval.HOUR: 60 * 60,
    Interval.DAILY: 60 * 60 * 24,
}

class TianqinClient:
    """
    Client for querying history data from Tianqin.
    """

    def __init__(self):
        """"""
        self.inited: bool = False
        self.symbols: set = set()
        self.api = None
        

    def init(self) -> bool: 
        """"""
        if self.inited:
            return True
        try:
            self.api = TqApi(TqKq(), auth="nimahannisha,tnt19860427")
            # 获得全部合约
            # self.symbols = [k for k, v in self.api._data["quotes"].items()]

            self.symbols = self.api.query_quotes(ins_class="FUTURE", expired=False)

        except:
            return False

        self.inited = True
        return True

    def to_tq_symbol(self, symbol: str, exchange: Exchange) -> str:
        """
        TQSdk exchange first
        """
        for count, word in enumerate(symbol):
            if word.isdigit():
                break

        # Check for index symbol
        time_str = symbol[count:]
        if time_str in ["88"]:
            return f"KQ.m@{exchange}.{symbol[:count]}"
        if time_str in ["99"]:
            return f"KQ.i@{exchange}.{symbol[:count]}"

        return f"{exchange.value}.{symbol}"

    def query_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        """
        Query history bar data from TqSdk.
        """
        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        start = req.start
        end = req.end

        tq_symbol = self.to_tq_symbol(symbol, exchange)
        if tq_symbol not in self.symbols:
            return None

        tq_interval = INTERVAL_VT2TQ.get(interval)
        if not tq_interval:
            return None

        # For querying night trading period data
        end += timedelta(1)

        # Only query open interest for futures contract
        # 只能用来补充最新的数据，无法指定日期
        df = self.api.get_kline_serial(tq_symbol, tq_interval, 8000).sort_values(by=["datetime"])

        # 时间戳对齐
        df["datetime"] = pd.to_datetime(df["datetime"] + TIME_GAP)

        #  去掉时区 by jarod
        df['datetime'] = df['datetime'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))
        df['datetime'] = pd.to_datetime(df['datetime'])
        start = start.strftime('%Y-%m-%d %H:%M:%S')
        start = pd.to_datetime(start)
        end = end.strftime('%Y-%m-%d %H:%M:%S')
        end = pd.to_datetime(end)
        
        # 过滤开始结束时间
        df = df[(df['datetime'] >= start - timedelta(days=1)) & (df['datetime'] < end)]
        
        data: List[BarData] = []

        if df is not None:
            for ix, row in df.iterrows():
                bar = BarData(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    datetime=row["datetime"].to_pydatetime(),
                    open_price=row["open"],
                    high_price=row["high"],
                    low_price=row["low"],
                    close_price=row["close"],
                    volume=row["volume"],
                    open_interest=row.get("open_oi", 0),
                    gateway_name="TQ",
                )
                data.append(bar)
        return data


# 使用天勤SDK替换RQData，一次只能下载8000条数据，可以用于补充运行时的数据
RqdataClient = TianqinClient
rqdata_client = TianqinClient()