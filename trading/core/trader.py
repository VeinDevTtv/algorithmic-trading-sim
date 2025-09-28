from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .order import Order


@dataclass
class Trader:
    trader_id: str
    balance: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)
    order_history: List[Order] = field(default_factory=list)

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


