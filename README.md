Algorithmic Trading Simulator

Production-quality matching engine, order book, and FastAPI server with a minimal UI. Includes bots, candles aggregation, and a benchmark harness.

### Features
- **Matching engine**: FIFO and PRO_RATA, fees, stop-loss, stop-limit, trailing stops, iceberg orders
- **Order book**: price-time priority, top-of-book depth snapshots
- **Risk controls**: notional caps, exposure limits, risk-per-trade
- **FastAPI server**: `/api/depth`, `/api/trades`, `/api/candles` and a no-build HTML UI
- **Bots**: random order flow generator
- **Benchmark**: orders/sec and trades/sec on your machine

### Architecture
Render `assets/architecture.mmd` with Mermaid. Quick view at mermaid.live.

```1:999:assets/architecture.mmd
flowchart TD
  subgraph Client
    UI[Browser UI]
  end
  subgraph Server[FastAPI Server]
    API[/REST Endpoints\n/api/depth\n/api/trades\n/api/candles/]
  end
  subgraph Core[Trading Core]
    ME[MatchingEngine]
    OB[OrderBook]
    TRD[Trader]
    TRADES[(Trades List)]
    RISK[Risk Checks]
    ICE[Iceberg\nStop/Trailing]
  end
  subgraph Analytics
    OHLC[CandleAggregator]
  end
  subgraph Sim
    BOTS[RandomBots\nBotScheduler]
  end

  UI -->|HTTP| API
  API --> ME
  ME <--> OB
  ME --> TRADES
  ME --> RISK
  ME --> ICE
  ME --> OHLC
  BOTS -->|Orders| ME
  OHLC -->|Candles| API
  OB -->|Depth| API
  TRADES -->|Recent| API
```

### Quick start
1) Create venv and install
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e .
```

2) Run the server
```bash
uvicorn server.app:app --reload --port 8000
```

3) Open the UI
Visit `http://localhost:8000` to see order book, trades, and candles.

API Endpoints:
- GET `/api/depth` → top-of-book depth
- GET `/api/trades` → recent trades
- GET `/api/candles` → recent 1m candles

### Sample usage (programmatic)
```python
from trading.core import MatchingEngine, OrderBook, OrderFactory, OrderSide

book = OrderBook(symbol="AAPL")
engine = MatchingEngine(order_book=book)

buy = OrderFactory.create_limit("o1", OrderSide.BUY, price=100.0, quantity=5.0, symbol="AAPL")
sell = OrderFactory.create_limit("o2", OrderSide.SELL, price=99.5, quantity=3.0, symbol="AAPL")

engine.submit_order(buy)
engine.submit_order(sell)
print(len(engine.trades))  # trades executed
```

### Benchmarks
Run on your machine:
```bash
python scripts/benchmark.py --orders 100000 --strategy FIFO --ioc-ratio 0.3
```

Example (my laptop):
```
Strategy        : FIFO
Orders          : 50,000
Trades          : 17,537
Duration (s)    : ~1.07
Orders / second : ~46,700
Trades / second : ~16,400
```

Note: numbers vary by hardware and Python version.

### Screenshots / GIFs
Add your captures to `assets/` and reference them here:
- `assets/screenshot_ui.png`
- `assets/screenshot_candles.png`
- `assets/demo.gif`

### Tests
```bash
pytest -q
```

### License
MIT — see `LICENSE`.


