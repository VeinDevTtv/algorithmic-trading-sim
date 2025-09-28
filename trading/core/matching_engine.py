from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .enums import OrderSide
from .order import Order
from .order_book import OrderBook


@dataclass
class Trade:
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: float


@dataclass
class MatchingEngine:
    order_book: OrderBook
    trades: List[Trade] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Subscribe to order book updates (Observer)
        self.order_book.subscribe("order_added", self._on_order_added)

    def _on_order_added(self, event: str, order: Order) -> None:
        # Placeholder hook: attempt to match after each add
        self.match_orders()

    def match_orders(self) -> None:
        """Placeholder matching logic.

        For now, implement a minimal price-time priority match:
        - If the best bid price >= best ask price, match at the ask price.
        - Market orders cross the spread immediately.
        - Partial fills are supported.
        """
        bids = self.order_book.bids
        asks = self.order_book.asks

        def best_bid_price() -> Optional[float]:
            if not bids:
                return None
            p = bids[0].price
            return float("inf") if p is None else p

        def best_ask_price() -> Optional[float]:
            if not asks:
                return None
            p = asks[0].price
            return 0.0 if p is None else p

        while bids and asks:
            bb = bids[0]
            ba = asks[0]

            bid_price = best_bid_price()
            ask_price = best_ask_price()
            if bid_price is None or ask_price is None:
                break

            if bid_price < ask_price:
                break

            trade_qty = min(bb.quantity, ba.quantity)
            execution_price = ba.price if ba.price is not None else (bb.price or ask_price)
            if execution_price is None:
                execution_price = ask_price

            self.trades.append(
                Trade(
                    buy_order_id=bb.id if bb.side == OrderSide.BUY else ba.id,
                    sell_order_id=ba.id if bb.side == OrderSide.BUY else bb.id,
                    price=float(execution_price),
                    quantity=trade_qty,
                )
            )

            bb.quantity -= trade_qty
            ba.quantity -= trade_qty

            if bb.quantity <= 0:
                bids.pop(0)
            if ba.quantity <= 0:
                asks.pop(0)


