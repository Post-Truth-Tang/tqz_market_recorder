

from dataclasses import dataclass

from vnpy.trader.object import AccountData



@dataclass
class TQZAccountData(AccountData):
    """
    Add user_deposit、risk_float based on AccountData
    """

    def __post_init__(self):
        """ callback after __init__ """

        self.vt_accountid = f"{self.gateway_name}.{self.accountid}"
        self.available = self.balance - self.frozen
        self.use_deposit = self.balance - self.available

        if self.balance is 0:
            self.risk_float = round(0, 4)
        else:
            self.risk_float = round(self.use_deposit / self.balance, 4)
