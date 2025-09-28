## Step 4 — Risk Management & Trader Features

This step adds realistic trading constraints and safety mechanisms to the core, introduces stop-loss orders, basic risk checks, and simple reporting for P&L and positions.

### What’s new
- **Stop-loss orders**: New `OrderType.STOP_LOSS`, validated in `Order`, created via `OrderFactory.create_stop_loss(...)`.
- **Risk checks on submission**: `MatchingEngine.submit_order(...)` enforces balance, per-order notional caps, risk-per-trade fraction, and max exposure per symbol.
- **Stop activation**: Engine tracks `last_trade_price` and automatically converts triggered stop-loss orders into market orders.
- **Trader enhancements**: Risk configuration fields and simple P&L helpers; continued `order_history` and `positions` tracking.
- **Reporting**: `pnl_report(trader_id)` and `position_report(trader_id)` on the engine.

### API additions and behavior changes
- `trading.core.enums.OrderType` now includes `STOP_LOSS`.
- `Order` validation:
  - `MARKET`: `price` must be `None`.
  - `LIMIT`: `price > 0`.
  - `STOP_LOSS`: `price > 0` (interpreted as the stop trigger price).
- `OrderFactory`:
  - `create_stop_loss(order_id, side, stop_price, quantity, timestamp=None, symbol=None, trader_id=None)`
  - `from_dict(...)` now accepts `type=STOP_LOSS` and routes accordingly.
- `OrderBook.add_order` will reject `STOP_LOSS` orders. Submit all stop orders via the engine.
- `MatchingEngine`:
  - `submit_order(order)`: performs risk checks (if a `Trader` is registered for `order.trader_id`), records the order to that trader, and either enqueues a stop or routes to the order book.
  - Maintains `last_trade_price` and calls `_activate_stop_orders()` after executions.
  - Reporting helpers: `pnl_report(trader_id)` and `position_report(trader_id)`.
- `Trader` risk and P&L fields:
  - `max_exposure_per_symbol: Optional[float]`
  - `max_order_notional: Optional[float]`
  - `risk_per_trade_fraction: Optional[float]` (e.g. `0.01` for 1%)
  - `daily_loss_limit: Optional[float]` (defined; enforcement to be extended)
  - P&L helpers: `mark_price(symbol, price)`, `realized_pnl()`, `unrealized_pnl()`, `total_equity()`

### Stop-loss mechanics
- A `STOP_LOSS` is held in the engine until triggered.
- Trigger evaluation uses `last_trade_price` on the engine for the relevant `symbol`.
  - For a SELL stop: triggers when `last_trade_price <= stop_price` → converted to a `MARKET` SELL.
  - For a BUY stop: triggers when `last_trade_price >= stop_price` → converted to a `MARKET` BUY.
- Converted market orders pass through the same `submit_order` flow (risk checks included) before being placed on the book.

### Risk checks (performed on submit)
- **Per-order notional cap**: `notional(order) <= trader.max_order_notional` (if set).
- **Risk-per-trade fraction**: `notional(order) <= trader.total_equity() * trader.risk_per_trade_fraction` (if set).
- **Balance check for BUY**: `trader.balance >= notional(order)` (if notional known).
- **Max exposure per symbol**: `abs(projected_position) <= trader.max_exposure_per_symbol` (if set).

Notional estimation for market orders uses engine `last_trade_price`, falling back to best book price if available; otherwise the check is skipped.

### P&L and reporting
- When trades execute:
  - Buyer cash decreases by `price * qty` and position increases.
  - Seller cash increases and position decreases.
  - Engine marks `last_trade_price` and calls `Trader.mark_price(symbol, price)` for all registered traders (simple mark-to-market).
  - Seller accrues a basic realized P&L equal to proceeds; this is a placeholder until cost-basis tracking is implemented.
- Reporting:
  - `MatchingEngine.pnl_report(trader_id)` → `{ realized, unrealized, equity, cash }`
  - `MatchingEngine.position_report(trader_id)` → `{ symbol: quantity }`

### Usage examples
Create and submit a stop-loss, with basic risk settings:

```python
from trading.core import OrderFactory, OrderSide, OrderBook, MatchingEngine, Trader

ob = OrderBook(symbol="AAPL")
engine = MatchingEngine(order_book=ob)

trader = Trader(
    trader_id="t1",
    balance=10000.0,
    max_order_notional=5000.0,
    max_exposure_per_symbol=100.0,
    risk_per_trade_fraction=0.1,
)
engine.register_trader(trader)

# Place a limit buy
engine.submit_order(
    OrderFactory.create_limit(
        order_id="b1", side=OrderSide.BUY, price=100.0, quantity=10, symbol="AAPL", trader_id="t1"
    )
)

# Place a protective stop-loss sell for the same quantity
engine.submit_order(
    OrderFactory.create_stop_loss(
        order_id="sl1", side=OrderSide.SELL, stop_price=90.0, quantity=10, symbol="AAPL", trader_id="t1"
    )
)

# Later, query reports
print(engine.position_report("t1"))
print(engine.pnl_report("t1"))
```

### Data structures and algorithms
- **Trade/order history**: maintained as Python lists (dynamic arrays) on `Trader.order_history`. This supports O(1) appends and is simple for iteration and reporting. If frequent deletions or reordering become critical, consider a linked-list or deque.
- **Stop orders**: tracked as a simple list in the engine and filtered/activated after executions. For higher throughput, consider indexing stops by side and threshold, or using a heap/ordered map keyed on stop price.
- **Risk validation**: direct dictionary lookups for balances and positions keep checks O(1). Notional estimation is O(1) using cached `last_trade_price` or current best quotes.

### File-level changes
- `trading/core/enums.py`: added `STOP_LOSS` to `OrderType`.
- `trading/core/order.py`: validation for `STOP_LOSS`.
- `trading/core/order_factory.py`: `create_stop_loss(...)` and `from_dict` support.
- `trading/core/order_book.py`: rejects `STOP_LOSS` on `add_order(...)` with a clear error.
- `trading/core/trader.py`: risk configuration fields; P&L helpers; continued history/positions.
- `trading/core/matching_engine.py`: `submit_order(...)`, risk checks, stop activation, `last_trade_price`, and reporting helpers.

### Limitations and next steps
- **Daily loss limit**: field exists on `Trader` but enforcement windowing (per-day resets) is not yet implemented.
- **P&L realism**: realized P&L currently treats proceeds as gain without cost basis. Add average price or FIFO/LIFO cost-basis tracking.
- **Stop evaluation**: relies on `last_trade_price`; consider supporting quote-based triggers or per-symbol last price.
- **Testing**: extend tests to cover stop triggers, risk rejections, and reporting.

This step brings practical safety features into the simulator while keeping APIs simple and extensible.


