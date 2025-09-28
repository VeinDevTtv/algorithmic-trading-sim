## Step 6 – Feature-Rich, Multi-Instrument Simulator

This step adds realistic order types, multi-instrument support, maker/taker fees, robust PnL tracking, and switchable matching algorithms.

### What's New
- **Order types**: `STOP_LOSS`, `STOP_LIMIT`, `TRAILING_STOP`, `ICEBERG`
- **Time-in-Force**: `GTC` and `IOC`
- **Multi-instrument**: one `OrderBook` per symbol, symbol-scoped state
- **Fees**: maker/taker fees applied on every fill
- **PnL**: per-symbol average price, realized and unrealized PnL
- **Matching algorithms**: `FIFO` (price-time) and `PRO_RATA` (top level allocation)

---

## 1) New Order Types

All advanced order types are routed through the `MatchingEngine` (not directly to the `OrderBook`).

### Stop Orders
- `STOP_LOSS`: triggers a market order when the price crosses the stop.
- `STOP_LIMIT`: triggers a limit order at an auxiliary limit price when the stop is hit.

Usage:
```python
from trading import OrderFactory

# Stop-Loss SELL: triggers market sell when last price <= 95
o1 = OrderFactory.create_stop_loss(
    "s1", "SELL", stop_price=95.0, quantity=100, symbol="AAPL", trader_id="T1"
)

# Stop-Limit SELL: triggers limit sell at 94.5 when last price <= 95
o2 = OrderFactory.create_stop_limit(
    "s2", "SELL", stop_price=95.0, limit_price=94.5, quantity=100, symbol="AAPL", trader_id="T1"
)
engine.submit_order(o1)
engine.submit_order(o2)
```

Triggering is symbol-scoped using `last_trade_price_by_symbol`.

### Trailing Stops
- `TRAILING_STOP`: maintains a dynamic stop price based on the highest high (for SELL) or lowest low (for BUY) observed, offset by `trailing_offset`.

Usage:
```python
o3 = OrderFactory.create_trailing_stop(
    "t1", "SELL", trailing_offset=2.0, quantity=100, symbol="AAPL", trader_id="T1"
)
engine.submit_order(o3)
```

Notes:
- For SELL trailing stops, stop = max_high − offset.
- For BUY trailing stops, stop = min_low + offset.

### Iceberg Orders
- `ICEBERG`: large order that displays only a `display_quantity` at a time. The engine maintains the parent order and posts child limit slices to the book.

Usage:
```python
o4 = OrderFactory.create_iceberg(
    "i1", "BUY", price=100.0, total_quantity=1000, display_quantity=100,
    symbol="AAPL", trader_id="T2"
)
engine.submit_order(o4)
```

Behavior:
- The engine posts the first visible child slice to the book.
- When a slice fully fills and is removed, the engine automatically posts the next slice until the hidden reserve is depleted.

### Time-in-Force (TIF)
- `GTC` (default): remains on the book until filled or canceled.
- `IOC`: attempts immediate match; any remainder is canceled.

Usage:
```python
o5 = OrderFactory.create_limit(
    "l1", "BUY", price=100.0, quantity=10, symbol="AAPL", trader_id="T1", tif="IOC"
)
engine.submit_order(o5)
```

Constraints:
- Advanced order types (`STOP_LOSS`, `STOP_LIMIT`, `TRAILING_STOP`, `ICEBERG`) cannot be added directly to `OrderBook` and must be submitted via `MatchingEngine`.

---

## 2) Multiple Instruments

The engine manages many symbols concurrently.

- `MatchingEngine.order_books`: `Dict[symbol, OrderBook]`
- `MatchingEngine.add_order_book(book)`: register additional books
- `MatchingEngine.match_orders(symbol=...)`: match within a specific symbol
- `MatchingEngine.cancel_order(order_id, symbol=...)`: cancel within a symbol
- Prices, triggers, and PnL are tracked per symbol using `last_trade_price_by_symbol`.

Usage:
```python
from trading import OrderBook, MatchingEngine

book_aapl = OrderBook(symbol="AAPL")
book_msft = OrderBook(symbol="MSFT")
engine = MatchingEngine(order_book=book_aapl)
engine.add_order_book(book_msft)

# Route by symbol using OrderFactory and submit via engine
```

---

## 3) Fees & PnL Tracking

### Fees
- Engine parameters: `maker_fee = 0.001`, `taker_fee = 0.002`.
- The engine identifies taker vs maker and applies fees to both sides accordingly.
- Fees are charged in quote currency and reflected in cash balance.

### PnL
- `Trader.apply_fill(...)` maintains per-symbol:
  - Position quantity
  - Average entry price
  - Realized PnL (on position reductions/crossovers)
  - Unrealized PnL (mark-to-market vs last price)
- Reports:
  - `engine.pnl_report(trader_id)`: summary of realized, unrealized, equity, cash
  - `engine.traders[trader_id].pnl_by_symbol()`: detailed per-instrument breakdown

Usage:
```python
summary = engine.pnl_report("T1")
by_symbol = engine.traders["T1"].pnl_by_symbol()
```

---

## 4) Matching Algorithms

Two strategies are supported:

### FIFO (Price-Time Priority)
- Default. Matches best price first, and within a price level uses arrival time priority.

### PRO_RATA (Top-of-Book Allocation)
- Allocates fills proportionally among orders at the best bid/ask price level.
- Market orders fall back to FIFO handling for fairness.

Select strategy:
```python
engine.matching_strategy = "FIFO"      # or "PRO_RATA"
```

---

## Breaking Changes & Notes

- Advanced orders (`STOP_*`, `TRAILING_STOP`, `ICEBERG`) must be submitted via `MatchingEngine` (not directly to `OrderBook`).
- `MatchingEngine.cancel_order` accepts an optional `symbol` for multi-instrument.
- Maker/taker classification is heuristic when both sides are limit; if one side is market, the market side is treated as taker.
- Trailing stops are updated using per-symbol last trade prices; offsets are absolute.
- Iceberg replenishment preserves price-time priority naturally via new child order timestamps.

---

## Quick Start Snippet

```python
from trading import OrderBook, MatchingEngine, OrderFactory

# 1) Books and engine
book_aapl = OrderBook(symbol="AAPL")
book_msft = OrderBook(symbol="MSFT")
engine = MatchingEngine(order_book=book_aapl)
engine.add_order_book(book_msft)
engine.matching_strategy = "PRO_RATA"  # or "FIFO"

# 2) Place some orders (IOC limit buy)
o = OrderFactory.create_limit(
    "o1", "BUY", price=100.0, quantity=50, symbol="AAPL", trader_id="T1", tif="IOC"
)
engine.submit_order(o)

# 3) Iceberg and trailing
ice = OrderFactory.create_iceberg(
    "i1", "SELL", price=101.0, total_quantity=1000, display_quantity=100,
    symbol="AAPL", trader_id="T2"
)
trail = OrderFactory.create_trailing_stop(
    "t1", "SELL", trailing_offset=2.0, quantity=100, symbol="AAPL", trader_id="T1"
)
engine.submit_order(ice)
engine.submit_order(trail)

# 4) PnL
print(engine.pnl_report("T1"))
print(engine.traders["T1"].pnl_by_symbol())
```

---

## Next Ideas
- Margin and leverage with maintenance margin liquidation
- More nuanced fee schedules (tiered or per-instrument)
- Persistent audit logs and trade IDs with sequence numbers
- Performance: depth aggregation and matching optimizations for large books


