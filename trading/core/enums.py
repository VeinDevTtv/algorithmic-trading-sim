from __future__ import annotations

from enum import Enum


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


