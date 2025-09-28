## Step 1: Core Classes & OOP Foundation

### Overview
This step establishes the backbone of the trading system using solid object‑oriented design. It introduces the core domain classes, applies two foundational design patterns (Factory Method and Observer), and ships a minimal yet functional matching loop. A small test suite validates creation and basic behaviors.

### What was implemented
- **Order**: Validated value object for individual orders (market/limit, buy/sell) with timezone‑aware timestamps.
- **Trader**: Tracks cash balance, positions by symbol, and order history.
- **OrderBook**: Manages bids/asks, supports add/remove, maintains price‑time priority ordering, and emits events.
- **MatchingEngine**: Subscribes to `OrderBook` events and performs a minimal price‑time match, recording executed trades.
- **OrderFactory**: Factory Method for creating `Order` instances from parameters or dictionaries.
- **Tests**: `pytest` suite covering object creation, order book sorting, and a basic match scenario.

### Package structure
```
trading/
  __init__.py
  core/
    __init__.py
    enums.py            # OrderType, OrderSide
    order.py            # Order dataclass + validation
    order_factory.py    # Factory Method (create_limit/create_market/from_dict)
    trader.py           # Trader balances, positions, history
    order_book.py       # Add/remove, sorting, Observer notifications
    matching_engine.py  # Minimal matching logic, records trades
tests/
  test_core.py
pyproject.toml          # pytest config
```

### Core components
- **Order (`trading/core/order.py`)**
  - **Attributes**: `id`, `type`, `side`, `price`, `quantity`, `timestamp` (timezone‑aware)
  - **Validation**:
    - Market: `price` must be `None`
    - Limit: `price` must be positive
    - `quantity` must be positive

- **Trader (`trading/core/trader.py`)**
  - **State**: `balance: float`, `positions: Dict[str, float]`, `order_history: List[Order]`
  - **Ops**: `deposit`, `withdraw`, `update_position`, `record_order`

- **OrderBook (`trading/core/order_book.py`)**
  - **State**: `bids: List[Order]`, `asks: List[Order]` for a given `symbol`
  - **Ops**: `add_order`, `remove_order`
  - **Ordering**:
    - Bids: highest price first; market treated as ∞ price
    - Asks: lowest price first; market treated as 0
  - **Observer**: `subscribe(event, handler)` and `_notify(event, order)` for `order_added`/`order_removed`

- **MatchingEngine (`trading/core/matching_engine.py`)**
  - Subscribes to `order_added` and calls `match_orders()`
  - Minimal price‑time matching:
    - Matches when best bid ≥ best ask
    - Supports partial fills
    - Execution price = ask price if available; otherwise falls back sensibly
  - Records `Trade` entries

- **OrderFactory (`trading/core/order_factory.py`)**
  - `create_limit(id, side, price, quantity, timestamp=None)`
  - `create_market(id, side, quantity, timestamp=None)`
  - `from_dict({...})` for ingestion/adapters

### Design patterns
- **Factory Method** (in `OrderFactory`): encapsulates object creation, normalizes inputs (strings/enums), and enforces per‑type invariants via the `Order` validator.
- **Observer** (between `OrderBook` and `MatchingEngine`): the engine subscribes to book events, enabling reactive matching and future extensibility (metrics, logging, streams).

### Data structures & algorithms
- **Lists** for bids/asks with per‑insert sorting ensure clear baseline behavior and simple invariants.
- **Priority ideas for Step 2**: swap to heaps/priority queues for `O(log n)` inserts while preserving price‑time priority via composite keys.

### Running the tests
1) Install pytest (if needed):
```bash
python -m pip install -q pytest
```
2) Execute the suite:
```bash
python -m pytest -q
```

Expected result: all tests pass.

### Notes on correctness and constraints
- All `datetime` timestamps are coerced to timezone‑aware (UTC) to avoid clock math issues.
- Market orders are represented with `price=None` and treated as best‑effort crossing in ordering/matching.
- `Trader.update_position` removes near‑zero entries to keep the positions map tidy.

### Next steps
- Strengthen `MatchingEngine` with richer rules (FIFO within price level, marketable limit behavior, tick size handling).
- Introduce cancellations, amendments, and order IDs indexing for `O(1)` lookup by id.
- Optimize `OrderBook` using priority queues or bucketed price levels.
- Extend tests to cover edge cases (partial fills across many levels, market sweeps, timestamp tie‑breaking).


