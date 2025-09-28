from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, DefaultDict, Dict, List, Optional

from .enums import OrderSide, OrderType, TimeInForce
from .order import Order
from .order_book import OrderBook


Subscriber = Callable[[str, object], None]


@dataclass
class Trade:
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: float
    timestamp: datetime


@dataclass
class MatchingEngine:
    order_book: OrderBook
    trades: List[Trade] = field(default_factory=list)
    traders: Dict[str, "Trader"] = field(default_factory=dict)
    last_trade_price: Optional[float] = None
    # Multi-instrument support
    order_books: Dict[str, OrderBook] = field(default_factory=dict)
    last_trade_price_by_symbol: Dict[str, float] = field(default_factory=dict)
    maker_fee: float = 0.001
    taker_fee: float = 0.002
    matching_strategy: str = "FIFO"  # or "PRO_RATA"
    # Store stop-loss orders keyed by (symbol, side) -> list of (stop_price, order)
    _stop_orders: List[Order] = field(default_factory=list)
    _stop_limit_orders: List[Order] = field(default_factory=list)
    _trailing_orders: List[Order] = field(default_factory=list)
    _subscribers: DefaultDict[str, List[Subscriber]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Subscribe to order book updates (Observer)
        self.order_book.subscribe("order_added", self._on_order_added)
        self.order_book.subscribe("order_removed", self._on_order_removed)
        # Register default book for multi-instrument map
        self.order_books[self.order_book.symbol] = self.order_book

    def add_order_book(self, book: OrderBook) -> None:
        if book.symbol in self.order_books:
            return
        self.order_books[book.symbol] = book
        book.subscribe("order_added", self._on_order_added)
        book.subscribe("order_removed", self._on_order_removed)

    def _get_book(self, symbol: Optional[str]) -> OrderBook:
        sym = symbol or self.order_book.symbol
        book = self.order_books.get(sym)
        if book is None:
            raise ValueError(f"Unknown symbol: {sym}")
        return book

    # --- Pub/Sub for external listeners (e.g., UI, server) ---
    def subscribe(self, event: str, handler: Subscriber) -> None:
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(handler)

    def unsubscribe(self, event: str, handler: Subscriber) -> None:
        handlers = self._subscribers.get(event)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:
            pass

    def _notify(self, event: str, payload: object) -> None:
        for handler in self._subscribers.get(event, []):
            handler(event, payload)

    def register_trader(self, trader: "Trader") -> None:
        self.traders[trader.trader_id] = trader

    # --- Risk and order submission ---
    def submit_order(self, order: Order) -> None:
        # Basic routing: validate risk, record, and either hold stop or add to book
        trader = self.traders.get(order.trader_id or "")
        if trader is not None:
            self._enforce_risk(trader, order)
            trader.record_order(order)
        book = self._get_book(order.symbol)
        if order.type == OrderType.STOP_LOSS:
            # Hold in engine until triggered
            self._stop_orders.append(order)
            return
        if order.type == OrderType.STOP_LIMIT:
            self._stop_limit_orders.append(order)
            return
        if order.type == OrderType.TRAILING_STOP:
            self._trailing_orders.append(order)
            # Initialize last trade anchor if needed
            last_px = self.last_trade_price_by_symbol.get(book.symbol, self.last_trade_price)
            if last_px is not None and order.price is None:
                # set initial stop from current price and offset depending on side
                if order.side == OrderSide.SELL:
                    order.price = last_px - (order.trailing_offset or 0)
                else:
                    order.price = last_px + (order.trailing_offset or 0)
            return
        if order.type == OrderType.ICEBERG:
            # Store parent iceberg and place first visible child
            self._submit_iceberg_parent(order)
            return
        book.add_order(order)
        # If IOC, attempt immediate match and cancel any remainder
        if order.tif == TimeInForce.IOC:
            self.match_orders(symbol=book.symbol)
            # If still has remaining quantity, cancel from book
            existing = book.get_order(order.id)
            if existing is not None and existing.quantity > 0:
                book.remove_order(order.id)

    def _estimate_notional(self, order: Order) -> Optional[float]:
        if order.type == OrderType.MARKET:
            ref = self.last_trade_price
            if ref is None:
                # fallback to book side
                best = (
                    self.order_book.best_ask() if order.side == OrderSide.BUY else self.order_book.best_bid()
                )
                ref = best.price if best and best.price is not None else None
            return None if ref is None else ref * order.quantity
        # LIMIT and STOP_LOSS have price
        if order.price is None:
            return None
        return order.price * order.quantity

    def _enforce_risk(self, trader: "Trader", order: Order) -> None:
        # Max order notional
        notional = self._estimate_notional(order)
        if trader.max_order_notional is not None and notional is not None:
            if notional > trader.max_order_notional:
                raise ValueError("Order exceeds trader's max order notional limit")

        # Risk per trade fraction of equity
        if trader.risk_per_trade_fraction is not None and notional is not None:
            if notional > trader.total_equity() * trader.risk_per_trade_fraction:
                raise ValueError("Order exceeds risk-per-trade fraction limit")

        # Balance sufficiency for BUY
        if order.side == OrderSide.BUY:
            if notional is not None and trader.balance < notional:
                raise ValueError("Insufficient balance for order notional")

        # Max exposure per symbol (absolute quantity)
        if trader.max_exposure_per_symbol is not None and order.symbol is not None:
            current_qty = trader.positions.get(order.symbol, 0.0)
            projected = current_qty + (order.quantity if order.side == OrderSide.BUY else -order.quantity)
            if abs(projected) > trader.max_exposure_per_symbol:
                raise ValueError("Order exceeds max exposure per symbol")

    def _on_order_added(self, event: str, order: Order) -> None:
        # Attempt to match only within the symbol's book
        sym = order.symbol or self.order_book.symbol
        self.match_orders(symbol=sym)

    def _on_order_removed(self, event: str, order: Order) -> None:
        # Replenish iceberg if this was a visible child
        parent_id = self._iceberg_child_to_parent.get(order.id)
        if parent_id is None:
            return
        parent = self._iceberg_parents.get(parent_id)
        if parent is None:
            return
        # Decrease remaining and spawn new child if needed
        remaining = self._iceberg_remaining.get(parent_id, 0.0)
        if remaining <= 0:
            # cleanup
            self._iceberg_parents.pop(parent_id, None)
            self._iceberg_remaining.pop(parent_id, None)
            return
        self._spawn_iceberg_child(parent_id)

    def _apply_trade_balances(self, buy: Order, sell: Order, price: float, quantity: float) -> None:
        buyer = self.traders.get(buy.trader_id or "")
        seller = self.traders.get(sell.trader_id or "")
        symbol = buy.symbol or sell.symbol or self.order_book.symbol
        # Determine maker/taker: if one side is MARKET, it's taker. Otherwise, default buyer as taker.
        buy_is_taker = buy.price is None and sell.price is not None
        sell_is_taker = sell.price is None and buy.price is not None
        if not buy_is_taker and not sell_is_taker:
            buy_is_taker = True
        buyer_fee = (self.taker_fee if buy_is_taker else self.maker_fee) * price * quantity
        seller_fee = (self.taker_fee if sell_is_taker else self.maker_fee) * price * quantity

        if buyer is not None:
            from .enums import OrderSide as _Side
            buyer.apply_fill(symbol, _Side.BUY, price, quantity, buyer_fee)
        if seller is not None:
            from .enums import OrderSide as _Side
            seller.apply_fill(symbol, _Side.SELL, price, quantity, seller_fee)
        self.last_trade_price = price
        self.last_trade_price_by_symbol[symbol] = price
        # mark to market all registered traders with same symbol
        for t in self.traders.values():
            t.mark_price(symbol, price)

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Optional[Order]:
        book = self._get_book(symbol)
        return book.remove_order(order_id)

    def match_orders(self, symbol: Optional[str] = None) -> None:
        """Matching within a single symbol's order book according to strategy."""
        book = self._get_book(symbol)
        if self.matching_strategy.upper() == "PRO_RATA":
            self._match_pro_rata(book)
            return
        # Default FIFO
        self._match_fifo(book)

    def _match_fifo(self, book: OrderBook) -> None:
        def best_bid_price() -> Optional[float]:
            bb = book.best_bid()
            if bb is None:
                return None
            p = bb.price
            return float("inf") if p is None else p

        def best_ask_price() -> Optional[float]:
            ba = book.best_ask()
            if ba is None:
                return None
            p = ba.price
            return 0.0 if p is None else p

        while True:
            bb = book.best_bid()
            ba = book.best_ask()
            if bb is None or ba is None:
                break

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

            buy_order = bb if bb.side == OrderSide.BUY else ba
            sell_order = ba if bb.side == OrderSide.BUY else bb
            trade = Trade(
                buy_order_id=buy_order.id,
                sell_order_id=sell_order.id,
                price=float(execution_price),
                quantity=trade_qty,
                timestamp=datetime.now(tz=timezone.utc),
            )
            self.trades.append(trade)
            self._apply_trade_balances(buy_order, sell_order, trade.price, trade.quantity)
            # Notify subscribers about trade execution
            self._notify("trade_executed", trade)

            bb.quantity -= trade_qty
            ba.quantity -= trade_qty

            if bb.quantity <= 0:
                book.remove_order(bb.id)
            if ba.quantity <= 0:
                book.remove_order(ba.id)

            # After each trade, check triggers
            self._activate_stop_orders(symbol=book.symbol)
            self._activate_stop_limit_orders(symbol=book.symbol)
            self._update_trailing_stops(symbol=book.symbol)
            self._activate_trailing_stops(symbol=book.symbol)
            # Update iceberg remaining for any child partially or fully filled
            self._update_iceberg_after_trade(bb)
            self._update_iceberg_after_trade(ba)

    def _match_pro_rata(self, book: OrderBook) -> None:
        # Only match at top of book price level, allocate proportionally
        def collect_level_orders(is_bid: bool) -> List[Order]:
            orders: List[Order] = []
            seen_ids: set = set()
            # Scan a snapshot of heap to collect orders at best price
            if is_bid:
                best = book.best_bid()
                if best is None or best.price is None:
                    return orders
                best_price = best.price
                # collect all orders with same price
                for _, _, _, oid in list(book._bid_heap):
                    if oid in seen_ids:
                        continue
                    o = book._orders_by_id.get(oid)
                    if o is None or o.price is None or o.quantity <= 0:
                        continue
                    if o.price == best_price and o.side == OrderSide.BUY:
                        orders.append(o)
                        seen_ids.add(oid)
            else:
                best = book.best_ask()
                if best is None or best.price is None:
                    return orders
                best_price = best.price
                for _, _, _, oid in list(book._ask_heap):
                    if oid in seen_ids:
                        continue
                    o = book._orders_by_id.get(oid)
                    if o is None or o.price is None or o.quantity <= 0:
                        continue
                    if o.price == best_price and o.side == OrderSide.SELL:
                        orders.append(o)
                        seen_ids.add(oid)
            return orders

        while True:
            bb = book.best_bid()
            ba = book.best_ask()
            if bb is None or ba is None:
                break
            if bb.price is None or ba.price is None:
                # Market orders: fall back to fifo for fairness
                self._match_fifo(book)
                break
            if bb.price < ba.price:
                break
            best_bid_price = bb.price
            best_ask_price = ba.price
            execution_price = best_ask_price

            bid_level_orders = collect_level_orders(is_bid=True)
            ask_level_orders = collect_level_orders(is_bid=False)
            if not bid_level_orders or not ask_level_orders:
                break
            total_bid_qty = sum(o.quantity for o in bid_level_orders)
            total_ask_qty = sum(o.quantity for o in ask_level_orders)
            match_qty = min(total_bid_qty, total_ask_qty)
            if match_qty <= 0:
                break

            # Allocate to asks proportionally based on their quantity, matched against bids in aggregate
            # For simplicity, iterate asks and pull from bids proportionally as well
            remaining_to_match = match_qty
            # Prepare iterators
            bid_iter = list(bid_level_orders)
            bi = 0
            for ask in ask_level_orders:
                if remaining_to_match <= 0:
                    break
                ask_share = (ask.quantity / total_ask_qty) * match_qty
                ask_fill = min(ask.quantity, ask_share, remaining_to_match)
                to_fill = ask_fill
                while to_fill > 0 and bi < len(bid_iter):
                    bid = bid_iter[bi]
                    if bid.quantity <= 0:
                        bi += 1
                        continue
                    fill_qty = min(bid.quantity, to_fill)
                    # Create trade between bid and ask
                    trade = Trade(
                        buy_order_id=(bid.id if bid.side == OrderSide.BUY else ask.id),
                        sell_order_id=(ask.id if ask.side == OrderSide.SELL else bid.id),
                        price=float(execution_price),
                        quantity=fill_qty,
                        timestamp=datetime.now(tz=timezone.utc),
                    )
                    self.trades.append(trade)
                    buy_order = bid if bid.side == OrderSide.BUY else ask
                    sell_order = ask if ask.side == OrderSide.SELL else bid
                    self._apply_trade_balances(buy_order, sell_order, trade.price, trade.quantity)
                    self._notify("trade_executed", trade)
                    bid.quantity -= fill_qty
                    ask.quantity -= fill_qty
                    to_fill -= fill_qty
                    remaining_to_match -= fill_qty
                    if ask.quantity <= 0:
                        book.remove_order(ask.id)
                    if bid.quantity <= 0:
                        book.remove_order(bid.id)
                # end inner while

            # Trigger mechanics after this batch
            self._activate_stop_orders(symbol=book.symbol)
            self._activate_stop_limit_orders(symbol=book.symbol)
            self._update_trailing_stops(symbol=book.symbol)
            self._activate_trailing_stops(symbol=book.symbol)

    def _activate_stop_orders(self, symbol: Optional[str] = None) -> None:
        if not self._stop_orders:
            return
        book = self._get_book(symbol)
        price_ref = self.last_trade_price_by_symbol.get(book.symbol, self.last_trade_price)
        if price_ref is None:
            return
        remaining: List[Order] = []
        for s in self._stop_orders:
            if s.symbol is not None and s.symbol != book.symbol:
                remaining.append(s)
                continue
            # Trigger conditions: for a SELL stop, trigger when price <= stop; for BUY stop, price >= stop
            if s.side == OrderSide.SELL and price_ref <= (s.price or 0):
                # Convert to market sell
                market = Order(
                    id=f"{s.id}-mkt",
                    type=OrderType.MARKET,
                    side=OrderSide.SELL,
                    price=None,
                    quantity=s.quantity,
                    timestamp=s.timestamp,
                    symbol=s.symbol or book.symbol,
                    trader_id=s.trader_id,
                    tif=s.tif,
                )
                self.submit_order(market)
            elif s.side == OrderSide.BUY and price_ref >= (s.price or float("inf")):
                market = Order(
                    id=f"{s.id}-mkt",
                    type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    price=None,
                    quantity=s.quantity,
                    timestamp=s.timestamp,
                    symbol=s.symbol or book.symbol,
                    trader_id=s.trader_id,
                    tif=s.tif,
                )
                self.submit_order(market)
            else:
                remaining.append(s)
        self._stop_orders = remaining

    def _activate_stop_limit_orders(self, symbol: Optional[str] = None) -> None:
        if not self._stop_limit_orders:
            return
        book = self._get_book(symbol)
        price_ref = self.last_trade_price_by_symbol.get(book.symbol, self.last_trade_price)
        if price_ref is None:
            return
        remaining: List[Order] = []
        for s in self._stop_limit_orders:
            if s.symbol is not None and s.symbol != book.symbol:
                remaining.append(s)
                continue
            trigger = (
                (s.side == OrderSide.SELL and price_ref <= (s.price or 0))
                or (s.side == OrderSide.BUY and price_ref >= (s.price or float("inf")))
            )
            if trigger:
                # Convert to limit order using aux_price
                limit = Order(
                    id=f"{s.id}-lmt",
                    type=OrderType.LIMIT,
                    side=s.side,
                    price=float(s.aux_price or 0.0),
                    quantity=s.quantity,
                    timestamp=s.timestamp,
                    symbol=s.symbol or book.symbol,
                    trader_id=s.trader_id,
                    tif=s.tif,
                )
                self.submit_order(limit)
            else:
                remaining.append(s)
        self._stop_limit_orders = remaining

    def _update_trailing_stops(self, symbol: Optional[str] = None) -> None:
        if not self._trailing_orders:
            return
        book = self._get_book(symbol)
        price_ref = self.last_trade_price_by_symbol.get(book.symbol, self.last_trade_price)
        if price_ref is None:
            return
        for t in self._trailing_orders:
            if t.symbol is not None and t.symbol != book.symbol:
                continue
            offset = t.trailing_offset or 0.0
            # For a SELL trailing stop, trail the highest price; stop = max_high - offset
            if t.side == OrderSide.SELL:
                # Use aux_price to store peak reference for trailing
                peak = t.aux_price if (t.aux_price is not None) else price_ref
                if price_ref > peak:
                    peak = price_ref
                t.aux_price = peak
                t.price = peak - offset
            else:
                # BUY trailing stop trails the lowest price; stop = min_low + offset
                trough = t.aux_price if (t.aux_price is not None) else price_ref
                if price_ref < trough:
                    trough = price_ref
                t.aux_price = trough
                t.price = trough + offset

    def _activate_trailing_stops(self, symbol: Optional[str] = None) -> None:
        if not self._trailing_orders:
            return
        book = self._get_book(symbol)
        price_ref = self.last_trade_price_by_symbol.get(book.symbol, self.last_trade_price)
        if price_ref is None:
            return
        remaining: List[Order] = []
        for s in self._trailing_orders:
            if s.symbol is not None and s.symbol != book.symbol:
                remaining.append(s)
                continue
            trigger = (
                (s.side == OrderSide.SELL and price_ref <= (s.price or 0))
                or (s.side == OrderSide.BUY and price_ref >= (s.price or float("inf")))
            )
            if trigger:
                market = Order(
                    id=f"{s.id}-mkt",
                    type=OrderType.MARKET,
                    side=s.side,
                    price=None,
                    quantity=s.quantity,
                    timestamp=s.timestamp,
                    symbol=s.symbol or book.symbol,
                    trader_id=s.trader_id,
                    tif=s.tif,
                )
                self.submit_order(market)
            else:
                remaining.append(s)
        self._trailing_orders = remaining

    # --- Iceberg management ---
    _iceberg_parents: Dict[str, Order] = field(default_factory=dict)
    _iceberg_remaining: Dict[str, float] = field(default_factory=dict)
    _iceberg_child_to_parent: Dict[str, str] = field(default_factory=dict)

    def _submit_iceberg_parent(self, parent: Order) -> None:
        self._iceberg_parents[parent.id] = parent
        self._iceberg_remaining[parent.id] = float(parent.quantity)
        self._spawn_iceberg_child(parent.id)

    def _spawn_iceberg_child(self, parent_id: str) -> None:
        parent = self._iceberg_parents.get(parent_id)
        if parent is None:
            return
        remaining = self._iceberg_remaining.get(parent_id, 0.0)
        if remaining <= 0:
            return
        slice_qty = min(float(parent.display_quantity or 0.0), float(remaining))
        if slice_qty <= 0:
            return
        child_id = f"{parent.id}-slice-{int(datetime.now(tz=timezone.utc).timestamp()*1e6)}"
        child = Order(
            id=child_id,
            type=OrderType.LIMIT,
            side=parent.side,
            price=parent.price,
            quantity=slice_qty,
            timestamp=datetime.now(tz=timezone.utc),
            symbol=parent.symbol or self.order_book.symbol,
            trader_id=parent.trader_id,
            tif=parent.tif,
        )
        self._iceberg_child_to_parent[child_id] = parent_id
        # Deduct from remaining and add to book
        self._iceberg_remaining[parent_id] = max(0.0, remaining - slice_qty)
        self.order_book.add_order(child)

    def _update_iceberg_after_trade(self, order: Optional[Order]) -> None:
        if order is None:
            return
        parent_id = self._iceberg_child_to_parent.get(order.id)
        if parent_id is None:
            return
        # If child fully filled, it will be removed and replenished on order_removed
        # If partially filled, keep as is; when it completes, removal handler will replenish

    # --- Simple reporting ---
    def pnl_report(self, trader_id: str) -> Dict[str, float]:
        t = self.traders.get(trader_id)
        if t is None:
            raise ValueError("Unknown trader")
        return {
            "realized": t.realized_pnl(),
            "unrealized": t.unrealized_pnl(),
            "equity": t.total_equity(),
            "cash": t.balance,
        }

    def position_report(self, trader_id: str) -> Dict[str, float]:
        t = self.traders.get(trader_id)
        if t is None:
            raise ValueError("Unknown trader")
        return dict(t.positions)


