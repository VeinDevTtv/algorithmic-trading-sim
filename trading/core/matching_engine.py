from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, DefaultDict, Dict, List, Optional

from .enums import OrderSide, OrderType
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
    # Store stop-loss orders keyed by (symbol, side) -> list of (stop_price, order)
    _stop_orders: List[Order] = field(default_factory=list)
    _subscribers: DefaultDict[str, List[Subscriber]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Subscribe to order book updates (Observer)
        self.order_book.subscribe("order_added", self._on_order_added)

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
        if order.type == OrderType.STOP_LOSS:
            # Hold in engine until triggered
            self._stop_orders.append(order)
            return
        self.order_book.add_order(order)

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
        # Placeholder hook: attempt to match after each add
        self.match_orders()

    def _apply_trade_balances(self, buy: Order, sell: Order, price: float, quantity: float) -> None:
        buyer = self.traders.get(buy.trader_id or "")
        seller = self.traders.get(sell.trader_id or "")
        total_cost = price * quantity
        symbol = buy.symbol or sell.symbol or self.order_book.symbol
        if buyer is not None:
            buyer.balance -= total_cost
            buyer.update_position(symbol, quantity)
        if seller is not None:
            seller.balance += total_cost
            seller.update_position(symbol, -quantity)
        # simplistic realized P&L: treat seller's proceeds as realized gain relative to zero cost
        if seller is not None:
            seller.add_realized_pnl(total_cost)
        self.last_trade_price = price
        # mark to market all registered traders with same symbol
        for t in self.traders.values():
            t.mark_price(symbol, price)

    def cancel_order(self, order_id: str) -> Optional[Order]:
        return self.order_book.remove_order(order_id)

    def match_orders(self) -> None:
        """Price-time priority matching using best bid/ask from the order book."""
        def best_bid_price() -> Optional[float]:
            bb = self.order_book.best_bid()
            if bb is None:
                return None
            p = bb.price
            return float("inf") if p is None else p

        def best_ask_price() -> Optional[float]:
            ba = self.order_book.best_ask()
            if ba is None:
                return None
            p = ba.price
            return 0.0 if p is None else p

        while True:
            bb = self.order_book.best_bid()
            ba = self.order_book.best_ask()
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
                self.order_book.remove_order(bb.id)
            if ba.quantity <= 0:
                self.order_book.remove_order(ba.id)

            # After each trade, check stop-loss triggers
            self._activate_stop_orders()

    def _activate_stop_orders(self) -> None:
        if not self._stop_orders:
            return
        price_ref = self.last_trade_price
        if price_ref is None:
            return
        remaining: List[Order] = []
        for s in self._stop_orders:
            if s.symbol is not None and s.symbol != self.order_book.symbol:
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
                    symbol=s.symbol or self.order_book.symbol,
                    trader_id=s.trader_id,
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
                    symbol=s.symbol or self.order_book.symbol,
                    trader_id=s.trader_id,
                )
                self.submit_order(market)
            else:
                remaining.append(s)
        self._stop_orders = remaining

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


