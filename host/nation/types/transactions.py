from enum import Enum, auto


class PurchaseResult(Enum):
    SUCCESS = auto()
    INSUFFICIENT_FUNDS = auto()


class SellResult(Enum):
    SUCCESS = auto()
    INSUFFICIENT_AMOUNT = auto()
