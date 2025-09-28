from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from .enums import OrderSide, OrderType
from .order import Order


def _parse_side(side: Union[str, OrderSide]) -> OrderSide:
    if isinstance(side, OrderSide):
        return side
    normalized = str(side).strip().upper()
    return OrderSide(normalized)


def _parse_type(order_type: Union[str, OrderType]) -> OrderType:
    if isinstance(order_type, OrderType):
        return order_type
    normalized = str(order_type).strip().upper()
    return OrderType(normalized)


class OrderFactory:
    """Factory for constructing orders via the Factory Method pattern."""

    @staticmethod
    def create_limit(
        order_id: str,
        side: Union[str, OrderSide],
        price: float,
        quantity: float,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
        trader_id: Optional[str] = None,
    ) -> Order:
        ts = timestamp or datetime.now(tz=timezone.utc)
        return Order(
            id=order_id,
            type=OrderType.LIMIT,
            side=_parse_side(side),
            price=price,
            quantity=quantity,
            timestamp=ts,
            symbol=symbol,
            trader_id=trader_id,
        )

    @staticmethod
    def create_market(
        order_id: str,
        side: Union[str, OrderSide],
        quantity: float,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
        trader_id: Optional[str] = None,
    ) -> Order:
        ts = timestamp or datetime.now(tz=timezone.utc)
        return Order(
            id=order_id,
            type=OrderType.MARKET,
            side=_parse_side(side),
            price=None,
            quantity=quantity,
            timestamp=ts,
            symbol=symbol,
            trader_id=trader_id,
        )

    @staticmethod
    def create_stop_loss(
        order_id: str,
        side: Union[str, OrderSide],
        stop_price: float,
        quantity: float,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
        trader_id: Optional[str] = None,
    ) -> Order:
        ts = timestamp or datetime.now(tz=timezone.utc)
        return Order(
            id=order_id,
            type=OrderType.STOP_LOSS,
            side=_parse_side(side),
            price=stop_price,
            quantity=quantity,
            timestamp=ts,
            symbol=symbol,
            trader_id=trader_id,
        )

    @staticmethod
    def from_dict(values: Dict[str, Any]) -> Order:
        """Create an order from a plain dictionary.

        Expected keys: id, type, side, quantity; price optional depending on type.
        """
        order_type = _parse_type(values["type"])  # may raise KeyError/ValueError
        side = _parse_side(values["side"])  # may raise KeyError/ValueError
        order_id = str(values["id"])  # may raise KeyError
        quantity = float(values["quantity"])  # may raise KeyError/ValueError
        price = values.get("price")
        ts = values.get("timestamp")
        timestamp = ts if isinstance(ts, datetime) else None
        symbol = values.get("symbol")
        trader_id = values.get("trader_id")

        if order_type == OrderType.MARKET:
            return OrderFactory.create_market(
                order_id=order_id,
                side=side,
                quantity=quantity,
                timestamp=timestamp,
                symbol=symbol,
                trader_id=trader_id,
            )
        if order_type == OrderType.STOP_LOSS:
            return OrderFactory.create_stop_loss(
                order_id=order_id,
                side=side,
                stop_price=float(price) if price is not None else None,
                quantity=quantity,
                timestamp=timestamp,
                symbol=symbol,
                trader_id=trader_id,
            )
        return OrderFactory.create_limit(
            order_id=order_id,
            side=side,
            price=float(price) if price is not None else None,  # validated by Order
            quantity=quantity,
            timestamp=timestamp,
            symbol=symbol,
            trader_id=trader_id,
        )


