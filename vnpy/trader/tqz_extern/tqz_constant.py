
from enum import Enum


class TQZFutureGatewaySettingKey(Enum):
    ACCOUNT_NAME = "用户名"
    PASS_WORD = "密码"
    BROKER_ID = "经纪商代码"
    TRADE_SERVER = "交易服务器"
    MARKET_SERVER = "行情服务器"
    PRODUCT_NAME = "产品名称"
    AUTHOR_CODE = "授权编码"
    PRODUCT_INFO = "产品信息"


class TQZStockGatewaySettingKey(Enum):
    ACCOUNT_ID = "账号"
    PASS_WORD = "密码"
    CUSTOMER_ID = "客户号"
    MARKET_ADDRESS = "行情地址"
    MARKET_PORT = "行情端口"
    TRADE_ADDRESS = "交易地址"
    TRADE_PORT = "交易端口"
    MARKET_PROTOCOL = "行情协议"
    AUTHOR_CODE = "授权码"


class TQZFuturesType(Enum):
    """
    Futures type of vt_symbol
    """

    COMMODITY_FUTURES = "COMMODITY_FUTURES"
    STOCK_INDEX_FUTURES = "STOCK_INDEX_FUTURES"
    TREASURY_FUTURES = "TREASURY_FUTURES"


class TQZJsonOperatorType(Enum):
    """
    Operator json file type
    """

    READ_TYPE = "r"
    WRITE_TYPE = "w"


class TQZCodingType(Enum):
    """
    Coding type
    """

    UTF_8_CODING = "utf-8"
    GBK_CODING = "gbk"


class TQZCffexSymbolType(Enum):
    """
    Cffex symbol
    """

    IC = "IC"
    IH = "IH"
    IF = "IF"

    T = "T"
    TF = "TF"
    TS = "TS"


class TQZPositionKeyType(Enum):
    """ """

    POSITION_KEY = "pos"
    ENTRYPRICE_KEY = "entryprice"
    TARGET_POSITION_KEY = "target_pos"
    TARGET_POSITION_ER_KEY = "target_position"

    BUY_POSITION_KEY = "buy_position"
    SELL_POSITION_KEY = "sell_position"
    NET_POSITION_KEY = "net_position"



class TQZWeekDayType(Enum):
    """
    Day of week
    """

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

class TQZAccountKeyType(Enum):
    """
    Key of account model.
    """

    ACCOUNT_ID_KEY = "account_id"
    BALANCE_KEY = "balance"
    AVAILABLE_KEY = "available"

    RISK_PERCENT_KEY = "risk_percent"


class TQZAccountNameType(Enum):
    """
    Type of account name
    """

    WEB_NAME = "web_name"
    UPPER_NAME = "upper_name"


class TQZCurrentFutureContractColumnType(Enum):
    """
    Column type of current-future-contract sheet
    """

    CONTRACT_CODE = "合约代码"
    CLOSE_PRICE_TODAY = "当日收盘价"
    OPEN_INTEREST_TODAY = "当日持仓量"
    CONTRACT_MULTI = "合约乘数"
    SEDIMENTARY_FUND_TODAY = "当日沉淀资金"