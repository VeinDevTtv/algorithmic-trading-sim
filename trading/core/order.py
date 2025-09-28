from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .enums import OrderSide, OrderType, TimeInForce


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
    symbol: Optional[str] = None
    trader_id: Optional[str] = None
    tif: TimeInForce = TimeInForce.GTC
    aux_price: Optional[float] = None  # e.g., limit price for STOP_LIMIT or initial stop for TRAILING_STOP
    trailing_offset: Optional[float] = None  # absolute offset for trailing stops
    display_quantity: Optional[float] = None  # visible slice for ICEBERG

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
        elif self.type == OrderType.STOP_LOSS:
            if self.price is None or self.price <= 0:
                raise ValueError("Stop-loss orders must have a positive stop price")
        elif self.type == OrderType.STOP_LIMIT:
            if self.price is None or self.price <= 0:
                raise ValueError("Stop-limit orders must have a positive stop price")
            if self.aux_price is None or self.aux_price <= 0:
                raise ValueError("Stop-limit orders must include a positive aux (limit) price")
        elif self.type == OrderType.TRAILING_STOP:
            # price here may serve as initial stop or may be None if offset provided
            if self.trailing_offset is None or self.trailing_offset <= 0:
                raise ValueError("Trailing-stop orders must include a positive trailing_offset")
        elif self.type == OrderType.ICEBERG:
            if self.price is None or self.price <= 0:
                raise ValueError("Iceberg orders must have a positive limit price")
            if self.display_quantity is None or self.display_quantity <= 0:
                raise ValueError("Iceberg orders must specify a positive display_quantity")
            if self.display_quantity > self.quantity:
                raise ValueError("display_quantity cannot exceed total quantity")
        else:
            raise ValueError(f"Unsupported order type: {self.type}")

        if self.side not in (OrderSide.BUY, OrderSide.SELL):
            raise ValueError(f"Unsupported order side: {self.side}")

        self.timestamp = _ensure_timezone_aware(self.timestamp)
        # Validate TIF
        if not isinstance(self.tif, TimeInForce):
            # allow string conversion for convenience
            try:
                self.tif = TimeInForce(str(self.tif))
            except Exception as exc:
                raise ValueError("Invalid TimeInForce value") from exc


