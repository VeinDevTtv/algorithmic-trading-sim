from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .order import Order


@dataclass
class Trader:
    trader_id: str
    balance: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)
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
            # Simple mark-to-market without average cost tracking
            # Assuming entry at 0 for demo; extend later with cost basis
            pnl += qty * price
        return pnl

    def total_equity(self) -> float:
        return self.balance + self.realized_pnl() + self.unrealized_pnl()


