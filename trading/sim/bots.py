from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from trading.core import MatchingEngine, OrderFactory, OrderSide, Trader


@dataclass(order=True)
class ScheduledEvent:
    scheduled_at: datetime
    seq: int
    action: callable = field(compare=False)


@dataclass
class RandomBot:
    trader: Trader
    symbol: str
    price_ref: float
    max_qty: float = 5.0
    price_spread: float = 1.0

    def next_action(self, engine: MatchingEngine) -> None:
        # place random buy or sell around price_ref +/- spread
        side = OrderSide.BUY if random.random() < 0.5 else OrderSide.SELL
        price_jitter = (random.random() * 2 - 1) * self.price_spread
        price = max(0.01, self.price_ref + price_jitter)
        qty = round(random.uniform(0.1, self.max_qty), 2)
        oid = f"{self.trader.trader_id}-{int(datetime.now(tz=timezone.utc).timestamp()*1000)}"
        order = OrderFactory.create_limit(
            order_id=oid,
            side=side,
            price=price,
            quantity=qty,
            symbol=self.symbol,
            trader_id=self.trader.trader_id,
        )
        try:
            engine.submit_order(order)
        except Exception:
            # ignore risk errors for simple sim; could log
            pass


@dataclass
class BotScheduler:
    engine: MatchingEngine
    bots: List[RandomBot]
    min_interval_ms: int = 150
    max_interval_ms: int = 800
    _queue: List[ScheduledEvent] = field(default_factory=list)
    _seq_counter: int = 0

    def _schedule(self, delay_ms: int, action) -> None:
        self._seq_counter += 1
        when = datetime.now(tz=timezone.utc) + timedelta(milliseconds=delay_ms)
        heapq.heappush(self._queue, ScheduledEvent(when, self._seq_counter, action))

    def start(self) -> None:
        # seed events for each bot
        for bot in self.bots:
            self._schedule(random.randint(self.min_interval_ms, self.max_interval_ms), lambda b=bot: self._run_bot(b))

    def _run_bot(self, bot: RandomBot) -> None:
        bot.next_action(self.engine)
        # reschedule
        self._schedule(random.randint(self.min_interval_ms, self.max_interval_ms), lambda b=bot: self._run_bot(b))

    def run_until(self, end_time: datetime) -> None:
        # simple discrete event loop; in a server we'd tick per request
        while self._queue and self._queue[0].scheduled_at <= end_time:
            evt = heapq.heappop(self._queue)
            evt.action()


