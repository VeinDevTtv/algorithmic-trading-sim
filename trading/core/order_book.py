from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Callable, DefaultDict, Dict, List, Optional, Set, Tuple

from .enums import OrderSide, OrderType
from .order import Order


Subscriber = Callable[[str, Order], None]


@dataclass
class OrderBook:
    symbol: str
    _orders_by_id: Dict[str, Order] = field(default_factory=dict)
    _subscribers: DefaultDict[str, List[Subscriber]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _bid_heap: List[Tuple[float, float, int, str]] = field(default_factory=list)
    _ask_heap: List[Tuple[float, float, int, str]] = field(default_factory=list)
    _removed_ids: Set[str] = field(default_factory=set)
    _seq_counter: int = 0

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
        if order.symbol is not None and order.symbol != self.symbol:
            raise ValueError("Order symbol does not match order book symbol")
        if order.type in (OrderType.STOP_LOSS, OrderType.STOP_LIMIT, OrderType.TRAILING_STOP, OrderType.ICEBERG):
            raise ValueError("This order type cannot be added directly to the order book; submit via engine")
        self._orders_by_id[order.id] = order
        # Compute heap key with price-time priority
        self._seq_counter += 1
        ts = order.timestamp.timestamp()
        if order.side == OrderSide.BUY:
            effective_price = float("inf") if order.price is None else float(order.price)
            # Max-heap via negative price; earlier timestamp first; seq to break ties
            key = (-effective_price, ts, self._seq_counter, order.id)
            heappush(self._bid_heap, key)
        else:
            effective_price = 0.0 if order.price is None else float(order.price)
            key = (effective_price, ts, self._seq_counter, order.id)
            heappush(self._ask_heap, key)
        self._notify("order_added", order)

    def remove_order(self, order_id: str) -> Optional[Order]:
        order = self._orders_by_id.pop(order_id, None)
        if order is None:
            return None
        self._removed_ids.add(order_id)
        self._notify("order_removed", order)
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders_by_id.get(order_id)


    # --- Best price retrieval helpers ---
    def _clean_top(self, heap: List[Tuple[float, float, int, str]]) -> None:
        while heap:
            _, _, _, oid = heap[0]
            order = self._orders_by_id.get(oid)
            if order is None or oid in self._removed_ids or order.quantity <= 0:
                heappop(heap)
                # If order existed but is now zero, ensure it's marked removed
                self._removed_ids.add(oid)
                continue
            break

    def best_bid(self) -> Optional[Order]:
        self._clean_top(self._bid_heap)
        if not self._bid_heap:
            return None
        oid = self._bid_heap[0][3]
        return self._orders_by_id.get(oid)

    def best_ask(self) -> Optional[Order]:
        self._clean_top(self._ask_heap)
        if not self._ask_heap:
            return None
        oid = self._ask_heap[0][3]
        return self._orders_by_id.get(oid)



    # --- Depth snapshot for visualization ---
    def depth(self, levels: int = 5) -> Dict[str, List[Tuple[float, float]]]:
        """Return top N levels for bids and asks as (price, cumulative_quantity).

        Market orders are ignored in the depth aggregation.
        """
        self._clean_top(self._bid_heap)
        self._clean_top(self._ask_heap)

        def top_levels(heap: List[Tuple[float, float, int, str]], is_bid: bool) -> List[Tuple[float, float]]:
            # Gather raw price levels
            prices: Dict[float, float] = {}
            seen: int = 0
            # We iterate a snapshot copy to avoid mutating the heap order
            for price_key, _, _, oid in sorted(heap):
                order = self._orders_by_id.get(oid)
                if order is None or order.price is None or oid in self._removed_ids or order.quantity <= 0:
                    continue
                px = float(order.price)
                prices[px] = prices.get(px, 0.0) + float(order.quantity)
                # Count unique price levels
                # For performance, exit early once enough unique levels collected
                # Will sort after aggregation.
            # Sort and truncate by side
            items = list(prices.items())
            items.sort(key=lambda x: x[0], reverse=is_bid)
            items = items[:levels]
            # Convert to (price, size)
            return [(p, q) for p, q in items]

        bids = top_levels(self._bid_heap, True)
        asks = top_levels(self._ask_heap, False)
        return {"bids": bids, "asks": asks}
