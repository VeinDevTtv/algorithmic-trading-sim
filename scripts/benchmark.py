from __future__ import annotations

import argparse
import random
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import sys
from pathlib import Path

# Allow running without installation by adding repo root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from trading.core import MatchingEngine, OrderBook, OrderFactory
from trading.core.enums import OrderSide, TimeInForce


@dataclass
class BenchmarkResult:
    total_orders: int
    total_trades: int
    duration_seconds: float
    orders_per_second: float
    trades_per_second: float
    strategy: str


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def run_engine_benchmark(
    num_orders: int,
    symbol: str = "AAPL",
    price_anchor: float = 100.0,
    price_spread: float = 2.0,
    max_qty: float = 5.0,
    matching_strategy: str = "FIFO",
    ioc_ratio: float = 0.0,
) -> BenchmarkResult:
    """Submit num_orders random limit/IOC orders and measure throughput."""

    ob = OrderBook(symbol=symbol)
    engine = MatchingEngine(order_book=ob, matching_strategy=matching_strategy)

    # Pre-warm the book with some liquidity
    seed = max(1000, min(5000, num_orders // 20))
    for i in range(seed):
        side = OrderSide.BUY if (i % 2 == 0) else OrderSide.SELL
        px_jitter = random.random() * price_spread
        price = price_anchor - px_jitter if side == OrderSide.BUY else price_anchor + px_jitter
        qty = 1.0 + random.random() * (max_qty - 1.0)
        order = OrderFactory.create_limit(
            order_id=f"seed-{i}",
            side=side,
            price=price,
            quantity=qty,
            timestamp=_now(),
            symbol=symbol,
        )
        engine.submit_order(order)

    start = time.perf_counter()
    trades_before = len(engine.trades)
    trade_counts: List[int] = []
    for i in range(num_orders):
        side = OrderSide.BUY if (i % 2 == 0) else OrderSide.SELL
        bias = (0.25 if side == OrderSide.BUY else -0.25) * price_spread
        px_jitter = random.random() * price_spread
        price = price_anchor - px_jitter + bias if side == OrderSide.BUY else price_anchor + px_jitter + bias
        qty = 1.0 + random.random() * (max_qty - 1.0)
        tif = TimeInForce.IOC if (ioc_ratio > 0 and random.random() < ioc_ratio) else TimeInForce.GTC
        order = OrderFactory.create_limit(
            order_id=f"ord-{i}",
            side=side,
            price=price,
            quantity=qty,
            timestamp=_now(),
            symbol=symbol,
            tif=tif,
        )
        engine.submit_order(order)
        if (i + 1) % 10_000 == 0:
            trade_counts.append(len(engine.trades) - trades_before)

    duration = max(1e-9, time.perf_counter() - start)
    total_trades = len(engine.trades) - trades_before
    ops = num_orders / duration
    tps = total_trades / duration

    engine.match_orders(symbol=symbol)

    _ = statistics.median(trade_counts) if trade_counts else total_trades

    return BenchmarkResult(
        total_orders=num_orders,
        total_trades=total_trades,
        duration_seconds=duration,
        orders_per_second=ops,
        trades_per_second=tps,
        strategy=matching_strategy,
    )


def main():
    parser = argparse.ArgumentParser(description="Benchmark MatchingEngine throughput")
    parser.add_argument("--orders", type=int, default=100_000, help="Number of orders to submit")
    parser.add_argument("--strategy", choices=["FIFO", "PRO_RATA"], default="FIFO", help="Matching strategy")
    parser.add_argument("--symbol", type=str, default="AAPL", help="Symbol")
    parser.add_argument("--price", type=float, default=100.0, help="Anchor price")
    parser.add_argument("--spread", type=float, default=2.0, help="Price spread range")
    parser.add_argument("--max-qty", type=float, default=5.0, help="Max order quantity")
    parser.add_argument("--ioc-ratio", type=float, default=0.0, help="Fraction of IOC orders [0..1]")
    args = parser.parse_args()

    res = run_engine_benchmark(
        num_orders=args.orders,
        symbol=args.symbol,
        price_anchor=args.price,
        price_spread=args.spread,
        max_qty=args.max_qty,
        matching_strategy=args.strategy,
        ioc_ratio=args.ioc_ratio,
    )

    print("=== MatchingEngine Benchmark ===")
    print(f"Strategy        : {res.strategy}")
    print(f"Orders          : {res.total_orders:,}")
    print(f"Trades          : {res.total_trades:,}")
    print(f"Duration (s)    : {res.duration_seconds:.3f}")
    print(f"Orders / second : {res.orders_per_second:,.0f}")
    print(f"Trades / second : {res.trades_per_second:,.0f}")


if __name__ == "__main__":
    main()


