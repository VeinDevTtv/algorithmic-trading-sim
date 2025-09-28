## Step 2: Implement Order Matching

This step makes the core trading engine functional. We added support for limit and market orders, implemented price–time priority matching with partial fills, updated trader balances and positions on execution, and enabled order cancellation. We also introduced hash maps to accelerate lookups and kept the design amenable to future heap-based optimizations.

### Highlights
- **Order types**: Limit and Market
- **Matching rule**: Execute when buy price ≥ sell price
- **Priority**: Price priority, then FIFO at a given price
- **Partial fills**: Supported; residuals remain in the book
- **Settlement**: Trader balances and positions updated per trade
- **Cancellation**: Remove by `order_id` efficiently
- **Data structures**: Sorted lists for best bid/ask, plus hash maps for O(1) lookups

---

## Changes by Component

### `trading/core/order.py`
- Added fields: `symbol: Optional[str]` and `trader_id: Optional[str]`.
- Validation retained for order types and side; timestamps normalized.

### `trading/core/order_factory.py`
- `create_limit` and `create_market` now accept `symbol` and `trader_id` and pass them to `Order`.
- `from_dict` supports optional `symbol` and `trader_id` keys.

### `trading/core/order_book.py`
- Added `_orders_by_id: Dict[str, Order]` for O(1) retrieval and cancellation.
- Enforced symbol consistency: an order’s `symbol` must match the book’s `symbol` if provided.
- Sorting semantics:
  - Bids: highest price first; Market treated as `+∞` for ordering.
  - Asks: lowest price first; Market treated as `0` for ordering.

### `trading/core/matching_engine.py`
- Introduced `traders: Dict[str, Trader]` registry and `register_trader(trader)`.
- `match_orders` executes trades when best bid ≥ best ask.
- Partial fills reduce quantities and remove fully filled orders.
- `_apply_trade_balances` debits buyer balance, credits seller, and updates positions.
- `cancel_order(order_id)` delegates to `OrderBook.remove_order`.

---

## Matching Logic (Price–Time Priority)
1. Identify best bid (highest) and best ask (lowest). Market orders are considered to cross the spread immediately by ordering as `+∞` for bids and `0` for asks.
2. If best bid price ≥ best ask price, a trade executes at the ask price.
3. Trade quantity is `min(bid.quantity, ask.quantity)`.
4. Apply settlement to buyer/seller balances and positions.
5. Remove any order whose `quantity` reaches zero; otherwise keep it with remaining quantity.
6. Repeat while the condition holds.

Notes:
- Execution price choice (ask price) mirrors common continuous limit order book conventions.
- Partial fills are natural consequences of `min(bid, ask)` sizing.

---

## Settlement Semantics
- **Buyer**: `balance -= price * quantity`, `positions[symbol] += quantity`.
- **Seller**: `balance += price * quantity`, `positions[symbol] -= quantity`.
- Symbol used is `order.symbol` or falls back to the `OrderBook.symbol`.

---

## Cancellation
- `MatchingEngine.cancel_order(order_id)` → `OrderBook.remove_order(order_id)`.
- `_orders_by_id` guarantees O(1) lookup and removal from the dictionary; list removal remains O(n), which is adequate for now and easily replaced by more advanced structures later.

---

## Data Structures and Complexity
- **Best bid/ask retrieval**: O(1) via front of sorted lists (`bids[0]`, `asks[0]`).
- **Insertion**: O(n log n) worst-case due to resorting lists after append. Future: replace with two heaps or a price-level map + FIFO queues for O(log n) inserts and O(1) best retrieval.
- **Cancellation**: O(1) to find by id via `_orders_by_id`, O(n) to remove from the list.
- **Matching loop**: O(k) where k is the number of matches executed in a call.

---

## Example Usage

```python
from trading.core import OrderBook, MatchingEngine, Trader, OrderFactory, OrderSide

# Setup
book = OrderBook(symbol="AAPL")
engine = MatchingEngine(order_book=book)

alice = Trader(trader_id="alice", balance=10_000.0)
bob = Trader(trader_id="bob", balance=10_000.0)
engine.register_trader(alice)
engine.register_trader(bob)

# Add a BUY limit order from Alice and a SELL limit order from Bob
book.add_order(
    OrderFactory.create_limit(
        order_id="b1", side=OrderSide.BUY, price=101.0, quantity=2.0,
        symbol="AAPL", trader_id="alice",
    )
)
book.add_order(
    OrderFactory.create_limit(
        order_id="a1", side=OrderSide.SELL, price=100.5, quantity=1.0,
        symbol="AAPL", trader_id="bob",
    )
)

# Matching happens on add; check results
assert len(engine.trades) == 1
tr = engine.trades[0]
assert tr.price == 100.5 and tr.quantity == 1.0

# Alice bought 1 AAPL, Bob sold 1 AAPL
assert alice.positions.get("AAPL", 0.0) == 1.0
assert bob.positions.get("AAPL", 0.0) == -1.0

# Cancel any remaining open order by id
engine.cancel_order("b1")
```

---

## Testing
- The provided unit tests validate order validation, book sorting, and basic matching with partial fills.
- Run tests:

```bash
python -m pytest -q
```

---

## Future Work
- Replace lists with heaps or price-level maps for O(log n) insertions and O(1) best retrieval.
- Extend order types (IOC, FOK, Iceberg) and add time-in-force controls.
- Add risk checks and pre-trade validation (e.g., insufficient balance prevention).
- Improve auditability: execution reports, order states, and detailed metrics.


