## Step 3: Advanced Order Book & Efficiency

### Goal

Optimize order management for speed and scalability by replacing basic list structures with efficient data structures, enforcing price–time priority, and providing O(1) best-price retrieval with O(log n) updates.

### What Changed

- **Heap-based OrderBook**
  - Replaced list-based `bids`/`asks` with two heaps and lazy deletion.
  - Added `best_bid()` and `best_ask()` for constant-time best-price access.
  - Implemented strict price–time priority with timestamp tie-breakers.

- **MatchingEngine integration**
  - Refactored to consume `best_bid()`/`best_ask()` directly.
  - Preserves partial fills and removes fully filled orders via `remove_order()`.

- **Tests updated**
  - Adjusted assertions to use `best_bid()`/`best_ask()` and validate book state after matching.

### Data Structures & Ordering

- Two heaps with stable tie-breaking:
  - **Bids (max-heap behavior):** store tuples `(-effective_price, timestamp, seq, order_id)`
  - **Asks (min-heap):** store tuples `(effective_price, timestamp, seq, order_id)`
- **Effective prices** for special cases:
  - Market buy: price treated as `+∞` (dominates bids)
  - Market sell: price treated as `0` (dominates asks)
- **Timestamp tie-breaker:** earlier `timestamp` wins when prices are equal.
- **Sequence number (`seq`)** provides a final deterministic tie-break within the same timestamp.

### API Highlights

- `OrderBook.add_order(order)` — O(log n)
- `OrderBook.remove_order(order_id)` — O(1) amortized via lazy deletion (actual heap cleanup happens when the order reaches the top)
- `OrderBook.best_bid()` / `OrderBook.best_ask()` — O(1) to peek; O(log n) amortized when cleaning stale tops

### Matching Logic (price–time priority)

Loop while both sides exist and crossable:
1. Get `bb = best_bid()` and `ba = best_ask()`
2. Compute `bid_price` and `ask_price` with market semantics (`∞` for bid-side market, `0` for ask-side market)
3. If `bid_price < ask_price`, stop; otherwise trade at the ask price (or best available when markets are involved)
4. Apply partial fills; decrement quantities
5. Remove orders via `remove_order()` when their quantity reaches zero

### Complexity

- **Insertion**: O(log n)
- **Best-price retrieval**: O(1) (after lazy cleanup)
- **Deletion/cancel**: O(1) amortized (mark removed, heap cleans lazily)
- **Match loop**: Each trade performs O(1) work plus at most O(log n) when an order is removed

### Correctness Notes

- **Price–time priority** is enforced across both sides via (price, timestamp, seq) ordering.
- **Market orders** are naturally prioritized across the spread by using effective prices.
- **Partial fills** do not reorder the queue; remaining quantity preserves original priority.
- **Cancellation** is O(1) amortized and safe; lazily removed entries are skipped during heap cleanup.
- **Symbol safety**: Adding an order with a mismatched symbol raises a `ValueError`.

### Tests & Validation

- Updated unit tests to assert on `best_bid()`/`best_ask()` instead of list indices.
- Verified matching produces expected trades and updates book state accordingly.
- Ran linters; no issues reported.

### Considerations & Next Steps

- **Range queries / depth snapshots**: Heaps optimize top-of-book access. For price bands and full depth, consider:
  - Augment with a `price -> deque[Order]` map (per-price FIFO queues), or
  - Switch to a **balanced BST** keyed by price with per-price queues, enabling efficient range queries and ordered traversal.
- **Throughput**: The heap + lazy deletion approach minimizes per-operation cost while maintaining deterministic priority.
- **Fairness**: Timestamp tie-break ensures FIFO within the same price level.

### References

- Building efficient order books with heaps and BSTs: `linkedin.com` discussion on stock exchange design.
- High-performance order book example: `github.com/sebastianhauer/orderbook`.
- Additional reading on fast limit order books and implementations in other languages: `github.com/vilas10/order-book`, `gist.github.com/halfelf`, `github.com/joaquinbejar/OrderBook-rs`.


