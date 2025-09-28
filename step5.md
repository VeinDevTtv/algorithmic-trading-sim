## Step 5: Market Simulation & Visualization

This step makes the simulator interactive and visually engaging by adding live trade events, an OHLC aggregator, random bot traders, a lightweight web server, and a simple in-browser UI.

### What’s included
- Matching engine trade event hooks and timestamps
- Order book depth snapshots for top-of-book visualization
- Streaming OHLC (1m) candle aggregation from executed trades
- Random bot traders scheduled via a priority queue
- FastAPI server exposing live APIs and serving a minimal UI

---

## Architecture Overview
- **Core**
  - `trading/core/matching_engine.py`: Publishes `trade_executed` events with timestamps.
  - `trading/core/order_book.py`: Provides `depth(levels)` aggregation of bids/asks.
- **Analytics**
  - `trading/analytics/ohlc.py`: `CandleAggregator` builds rolling 1m candles (open, high, low, close, volume, trades).
- **Simulation**
  - `trading/sim/bots.py`: `RandomBot` places limit orders around a price reference; `BotScheduler` uses a min-heap priority queue to schedule events.
- **Server + UI**
  - `server/app.py`: FastAPI app with endpoints for depth, trades, and candles; serves a minimal HTML/JS UI at `/` showing order book, recent trades, and candles.

---

## Data Structures & Algorithms Focus
- **Priority queues**: 
  - The order book maintains price-time priority using heaps.
  - The bot scheduler uses a min-heap to execute actions at scheduled timestamps.
- **Event-driven updates**: Matching engine exposes a pub/sub hook for `trade_executed`, enabling decoupled consumers (e.g., candle aggregation and UI).
- **Time bucketing**: OHLC aggregation aligns trades into fixed 60s buckets for smooth charting.

---

## Key Components
- **Trade Events**: `MatchingEngine` now emits `trade_executed` with a `timestamp` so downstream consumers can react in real time.
- **Depth Snapshot**: `OrderBook.depth(levels=5)` returns top N (price, size) levels per side for visualization.
- **OHLC Aggregation**: `CandleAggregator(symbol, period_seconds=60)` keeps a current candle, rolls closed candles to history, and emits updates.
- **Bots & Scheduler**: `RandomBot` generates realistic flow (random side, jittered price, bounded quantity). `BotScheduler` schedules each bot’s next action using a priority queue for near-real-time behavior.
- **FastAPI Server**:
  - `GET /api/depth` → top-of-book depth (configurable levels)
  - `GET /api/trades` → recent trades including timestamps
  - `GET /api/candles` → recent 1m candles
  - `GET /` → minimal UI (tables + canvas chart) polling the endpoints ~2Hz

---

## Run Locally

### 1) Install dependencies
```bash
python -m venv .venv && .venv\Scripts\activate   # Windows PowerShell
pip install -e .
```

### 2) Start the server
```bash
uvicorn server.app:app --reload --port 8000
```

### 3) Open the UI
Visit `http://localhost:8000` and watch:
- Order book depth update live
- Stream of recent trades
- 1-minute OHLC candlesticks rendered on a canvas

---

## Implementation Notes
- Bots are seeded at `AAPL` around a price anchor (100.0) and continuously submit limit orders; the matching engine’s price-time rules execute trades.
- Every executed trade updates trader balances/positions, marks last price, and is forwarded to the candle aggregator.
- The UI intentionally avoids a build step (no separate React dev server) for simplicity; it’s a single HTML page returned by FastAPI that polls JSON endpoints.

---

## Extensibility Ideas
- Add more strategies (market making, momentum, mean reversion) using the same scheduler.
- Swap the polling UI for Server-Sent Events or WebSockets for lower-latency streaming.
- Replace the minimal canvas chart with a richer React or Three.js visualization.
- Track average cost per position to compute realized/unrealized P&L more accurately.


