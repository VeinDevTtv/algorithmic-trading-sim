from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .order import Order
from .enums import OrderSide


@dataclass
class Trader:
    trader_id: str
    balance: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)
    _avg_price: Dict[str, float] = field(default_factory=dict)
    _realized_by_symbol: Dict[str, float] = field(default_factory=dict)
    order_history: List[Order] = field(default_factory=list)
    # Risk configuration
    max_exposure_per_symbol: Optional[float] = None  # absolute quantity cap per symbol
    max_order_notional: Optional[float] = None  # cap per order in currency units
    risk_per_trade_fraction: Optional[float] = None  # e.g., 0.01 for 1%
    daily_loss_limit: Optional[float] = None  # currency units; basic placeholder
    _realized_pnl: float = 0.0
    _unrealized_prices: Dict[str, float] = field(default_factory=dict)

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdraw amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        self.balance -= amount

    def record_order(self, order: Order) -> None:
        self.order_history.append(order)

    def update_position(self, symbol: str, delta_quantity: float) -> None:
        current = self.positions.get(symbol, 0.0)
        new_qty = current + delta_quantity
        if abs(new_qty) < 1e-12:
            self.positions.pop(symbol, None)
            self._avg_price.pop(symbol, None)
        else:
            self.positions[symbol] = new_qty

    # --- P&L helpers ---
    def mark_price(self, symbol: str, price: float) -> None:
        if price <= 0:
            return
        self._unrealized_prices[symbol] = price

    def add_realized_pnl(self, amount: float) -> None:
        self._realized_pnl += amount

    def realized_pnl(self) -> float:
        return self._realized_pnl

    def unrealized_pnl(self) -> float:
        pnl = 0.0
        for symbol, qty in self.positions.items():
            price = self._unrealized_prices.get(symbol)
            if price is None:
                continue
            avg = self._avg_price.get(symbol, 0.0)
            if qty > 0:
                pnl += (price - avg) * qty
            elif qty < 0:
                pnl += (avg - price) * (-qty)
        return pnl

    def total_equity(self) -> float:
        return self.balance + self.realized_pnl() + self.unrealized_pnl()

    # --- Execution handling with average price and realized PnL ---
    def apply_fill(self, symbol: str, side: OrderSide, price: float, quantity: float, fee_paid: float) -> None:
        if quantity <= 0:
            return
        # Cash movement including fees
        notional = price * quantity
        if side == OrderSide.BUY:
            self.balance -= notional
            self.balance -= fee_paid
        else:
            self.balance += notional
            self.balance -= fee_paid

        current_qty = self.positions.get(symbol, 0.0)
        avg = self._avg_price.get(symbol, price)

        if side == OrderSide.BUY:
            if current_qty >= 0:
                # Increasing/creating long
                new_qty = current_qty + quantity
                new_avg = ((avg * current_qty) + notional) / new_qty if new_qty != 0 else 0.0
                self.positions[symbol] = new_qty
                self._avg_price[symbol] = new_avg
            else:
                # Covering short
                cover_qty = min(quantity, -current_qty)
                realized = (avg - price) * cover_qty
                self._realized_pnl += realized
                self._realized_by_symbol[symbol] = self._realized_by_symbol.get(symbol, 0.0) + realized
                new_qty = current_qty + quantity
                if new_qty < 0:
                    # Still short; avg unchanged
                    self.positions[symbol] = new_qty
                elif new_qty > 0:
                    # Crossed into long; set new avg to trade price for remaining
                    self.positions[symbol] = new_qty
                    self._avg_price[symbol] = price
                else:
                    # Flat
                    self.positions.pop(symbol, None)
                    self._avg_price.pop(symbol, None)
        else:  # SELL
            if current_qty <= 0:
                # Increasing/creating short
                new_qty = current_qty - quantity
                # Use absolute quantities for avg calculation
                short_size_before = -current_qty
                short_size_after = -new_qty
                new_avg = ((avg * short_size_before) + notional) / short_size_after if short_size_after != 0 else 0.0
                self.positions[symbol] = new_qty
                self._avg_price[symbol] = new_avg
            else:
                # Reducing long
                sell_qty = min(quantity, current_qty)
                realized = (price - avg) * sell_qty
                self._realized_pnl += realized
                self._realized_by_symbol[symbol] = self._realized_by_symbol.get(symbol, 0.0) + realized
                new_qty = current_qty - quantity
                if new_qty > 0:
                    self.positions[symbol] = new_qty
                elif new_qty < 0:
                    # Crossed into short; set new avg to trade price for remaining
                    self.positions[symbol] = new_qty
                    self._avg_price[symbol] = price
                else:
                    # Flat
                    self.positions.pop(symbol, None)
                    self._avg_price.pop(symbol, None)

    # --- PnL breakdown per instrument ---
    def pnl_by_symbol(self) -> Dict[str, Dict[str, float]]:
        report: Dict[str, Dict[str, float]] = {}
        symbols = set(self.positions.keys()) | set(self._avg_price.keys()) | set(self._unrealized_prices.keys()) | set(self._realized_by_symbol.keys())
        for symbol in symbols:
            qty = self.positions.get(symbol, 0.0)
            avg = self._avg_price.get(symbol, 0.0)
            last = self._unrealized_prices.get(symbol)
            unreal = 0.0
            if last is not None:
                if qty > 0:
                    unreal = (last - avg) * qty
                elif qty < 0:
                    unreal = (avg - last) * (-qty)
            realized = self._realized_by_symbol.get(symbol, 0.0)
            report[symbol] = {
                "quantity": qty,
                "avg_price": avg,
                "last_price": last if last is not None else 0.0,
                "unrealized": unreal,
                "realized": realized,
            }
        return report
