from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, DefaultDict, Dict, List, Optional

from trading.core.matching_engine import Trade


@dataclass
class Candle:
    symbol: str
    start: datetime
    end: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    trades: int = 0


Subscriber = Callable[[str, Candle], None]


@dataclass
class CandleAggregator:
    symbol: str
    period_seconds: int = 60
    _current: Optional[Candle] = None
    _history: List[Candle] = field(default_factory=list)
    _subscribers: Dict[str, List[Subscriber]] = field(default_factory=dict)

    def subscribe(self, event: str, handler: Subscriber) -> None:
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(handler)

    def _notify(self, event: str, candle: Candle) -> None:
        for h in self._subscribers.get(event, []):
            h(event, candle)

    def _bucket_start(self, ts: datetime) -> datetime:
        # Align timestamp to bucket boundary
        sec = int(ts.timestamp())
        start_sec = sec - (sec % self.period_seconds)
        return datetime.fromtimestamp(start_sec, tz=timezone.utc)

    def add_trade(self, trade: Trade) -> None:
        ts = trade.timestamp
        start = self._bucket_start(ts)
        end = start + timedelta(seconds=self.period_seconds)
        price = float(trade.price)
        qty = float(trade.quantity)

        if self._current is None or not (self._current.start <= ts < self._current.end):
            # roll current
            if self._current is not None:
                self._history.append(self._current)
                self._notify("candle_closed", self._current)
            self._current = Candle(
                symbol=self.symbol,
                start=start,
                end=end,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=qty,
                trades=1,
            )
            self._notify("candle_updated", self._current)
            return

        # update current
        self._current.high = max(self._current.high, price)
        self._current.low = min(self._current.low, price)
        self._current.close = price
        self._current.volume += qty
        self._current.trades += 1
        self._notify("candle_updated", self._current)

    def current_candle(self) -> Optional[Candle]:
        return self._current

    def recent(self, limit: int = 100) -> List[Candle]:
        out = self._history[-limit:]
        if self._current is not None:
            out = out + [self._current]
        return out


