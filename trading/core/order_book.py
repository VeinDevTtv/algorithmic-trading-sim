from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, DefaultDict, Dict, List, Optional

from .enums import OrderSide
from .order import Order


Subscriber = Callable[[str, Order], None]


@dataclass
class OrderBook:
    symbol: str
    bids: List[Order] = field(default_factory=list)
    asks: List[Order] = field(default_factory=list)
    _subscribers: DefaultDict[str, List[Subscriber]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def subscribe(self, event: str, handler: Subscriber) -> None:
        self._subscribers[event].append(handler)

    def unsubscribe(self, event: str, handler: Subscriber) -> None:
        handlers = self._subscribers.get(event)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:
            pass

    def _notify(self, event: str, order: Order) -> None:
        for handler in self._subscribers.get(event, []):
            handler(event, order)

    def add_order(self, order: Order) -> None:
        if order.side == OrderSide.BUY:
            self.bids.append(order)
            # Highest price first for bids; market orders treated as price = inf
            self.bids.sort(key=lambda o: float("inf") if o.price is None else o.price, reverse=True)
        else:
            self.asks.append(order)
            # Lowest price first for asks; market orders treated as price = 0
            self.asks.sort(key=lambda o: 0.0 if o.price is None else o.price)
        self._notify("order_added", order)

    def remove_order(self, order_id: str) -> Optional[Order]:
        for book in (self.bids, self.asks):
            for idx, ord in enumerate(book):
                if ord.id == order_id:
                    removed = book.pop(idx)
                    self._notify("order_removed", removed)
                    return removed
        return None


