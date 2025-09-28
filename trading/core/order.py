from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .enums import OrderSide, OrderType


def _ensure_timezone_aware(ts: datetime) -> datetime:
    if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


@dataclass
class Order:
    id: str
    type: OrderType
    side: OrderSide
    price: Optional[float]
    quantity: float
    timestamp: datetime

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Order id must be a non-empty string")

        if self.quantity is None or self.quantity <= 0:
            raise ValueError("Order quantity must be a positive number")

        if self.type == OrderType.MARKET:
            if self.price is not None:
                raise ValueError("Market orders must have price set to None")
        elif self.type == OrderType.LIMIT:
            if self.price is None or self.price <= 0:
                raise ValueError("Limit orders must have a positive price")
        else:
            raise ValueError(f"Unsupported order type: {self.type}")

        if self.side not in (OrderSide.BUY, OrderSide.SELL):
            raise ValueError(f"Unsupported order side: {self.side}")

        self.timestamp = _ensure_timezone_aware(self.timestamp)


