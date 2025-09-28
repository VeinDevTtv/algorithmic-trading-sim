from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from .enums import OrderSide, OrderType, TimeInForce
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
        tif: Union[str, TimeInForce] = TimeInForce.GTC,
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
            tif=TimeInForce(tif) if not isinstance(tif, TimeInForce) else tif,
        )

    @staticmethod
    def create_market(
        order_id: str,
        side: Union[str, OrderSide],
        quantity: float,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
        trader_id: Optional[str] = None,
        tif: Union[str, TimeInForce] = TimeInForce.GTC,
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
            tif=TimeInForce(tif) if not isinstance(tif, TimeInForce) else tif,
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
        tif: Union[str, TimeInForce] = TimeInForce.GTC,
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
            tif=TimeInForce(tif) if not isinstance(tif, TimeInForce) else tif,
        )

    @staticmethod
    def create_stop_limit(
        order_id: str,
        side: Union[str, OrderSide],
        stop_price: float,
        limit_price: float,
        quantity: float,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
        trader_id: Optional[str] = None,
        tif: Union[str, TimeInForce] = TimeInForce.GTC,
    ) -> Order:
        ts = timestamp or datetime.now(tz=timezone.utc)
        return Order(
            id=order_id,
            type=OrderType.STOP_LIMIT,
            side=_parse_side(side),
            price=stop_price,
            quantity=quantity,
            timestamp=ts,
            symbol=symbol,
            trader_id=trader_id,
            tif=TimeInForce(tif) if not isinstance(tif, TimeInForce) else tif,
            aux_price=limit_price,
        )

    @staticmethod
    def create_trailing_stop(
        order_id: str,
        side: Union[str, OrderSide],
        trailing_offset: float,
        quantity: float,
        initial_price: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
        trader_id: Optional[str] = None,
        tif: Union[str, TimeInForce] = TimeInForce.GTC,
    ) -> Order:
        ts = timestamp or datetime.now(tz=timezone.utc)
        return Order(
            id=order_id,
            type=OrderType.TRAILING_STOP,
            side=_parse_side(side),
            price=initial_price,
            quantity=quantity,
            timestamp=ts,
            symbol=symbol,
            trader_id=trader_id,
            tif=TimeInForce(tif) if not isinstance(tif, TimeInForce) else tif,
            trailing_offset=trailing_offset,
        )

    @staticmethod
    def create_iceberg(
        order_id: str,
        side: Union[str, OrderSide],
        price: float,
        total_quantity: float,
        display_quantity: float,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
        trader_id: Optional[str] = None,
        tif: Union[str, TimeInForce] = TimeInForce.GTC,
    ) -> Order:
        ts = timestamp or datetime.now(tz=timezone.utc)
        return Order(
            id=order_id,
            type=OrderType.ICEBERG,
            side=_parse_side(side),
            price=price,
            quantity=total_quantity,
            timestamp=ts,
            symbol=symbol,
            trader_id=trader_id,
            tif=TimeInForce(tif) if not isinstance(tif, TimeInForce) else tif,
            display_quantity=display_quantity,
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
        tif_raw = values.get("tif", TimeInForce.GTC)
        tif = TimeInForce(tif_raw) if not isinstance(tif_raw, TimeInForce) else tif_raw

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
                tif=tif,
            )
        if order_type == OrderType.STOP_LIMIT:
            limit_px = values.get("aux_price")
            return OrderFactory.create_stop_limit(
                order_id=order_id,
                side=side,
                stop_price=float(price) if price is not None else None,
                limit_price=float(limit_px) if limit_px is not None else None,
                quantity=quantity,
                timestamp=timestamp,
                symbol=symbol,
                trader_id=trader_id,
                tif=tif,
            )
        if order_type == OrderType.TRAILING_STOP:
            trailing_offset = values.get("trailing_offset")
            return OrderFactory.create_trailing_stop(
                order_id=order_id,
                side=side,
                trailing_offset=float(trailing_offset) if trailing_offset is not None else None,
                quantity=quantity,
                initial_price=float(price) if price is not None else None,
                timestamp=timestamp,
                symbol=symbol,
                trader_id=trader_id,
                tif=tif,
            )
        if order_type == OrderType.ICEBERG:
            display_quantity = values.get("display_quantity")
            return OrderFactory.create_iceberg(
                order_id=order_id,
                side=side,
                price=float(price) if price is not None else None,
                total_quantity=quantity,
                display_quantity=float(display_quantity) if display_quantity is not None else None,
                timestamp=timestamp,
                symbol=symbol,
                trader_id=trader_id,
                tif=tif,
            )
        return OrderFactory.create_limit(
            order_id=order_id,
            side=side,
            price=float(price) if price is not None else None,  # validated by Order
            quantity=quantity,
            timestamp=timestamp,
            symbol=symbol,
            trader_id=trader_id,
            tif=tif,
        )


