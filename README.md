Algorithmic Trading Simulator

Production-quality matching engine, order book, and FastAPI server with a modern Next.js dashboard UI. Includes bots, candles aggregation, and a benchmark harness.

### Features
- **Matching engine**: FIFO and PRO_RATA, fees, stop-loss, stop-limit, trailing stops, iceberg orders
- **Order book**: price-time priority, top-of-book depth snapshots
- **Risk controls**: notional caps, exposure limits, risk-per-trade
- **FastAPI server**: `/api/depth`, `/api/trades`, `/api/candles`
- **Web UI (Next.js + shadcn/ui)**:
  - Left: Order Book (DataTable with bid/ask tint + depth overlay) and Market Depth
  - Right: Recent Trades (virtualized list with badges) and PnL/Positions
  - Bottom: Candlestick + Volume (Lightweight Charts) and Order Entry (Tabs: Market/Limit/Stop)
  - Theme toggle (light/dark), responsive layout, accessible ARIA labels
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

3) Start the Web UI (Next.js dashboard)
```bash
cd web
npm install
npm run dev
```
Visit `http://localhost:3000` for the dashboard UI.

API Endpoints:
- GET `/api/depth` → top-of-book depth
- GET `/api/trades` → recent trades
- GET `/api/candles` → recent 1m candles

To wire the dashboard to live data, adapt the sample data in `web/src/app/page.tsx` and the UI components in `web/src/components/**` to fetch from these endpoints.

### Web UI details
- Codebase: `web/` (Next.js 15, Tailwind v4, shadcn/ui)
- Theming: `next-themes` with a `ThemeToggle` in `web/src/components/theme-toggle.tsx`
- UI components: shadcn/ui (`button`, `card`, `table`, `tabs`, `select`, `tooltip`, `sheet`, `drawer`, `switch`, `scroll-area`, `separator`)
- Charts: `lightweight-charts` (dynamically imported and client-only)
- Virtualization: `@tanstack/react-virtual` for Recent Trades
- Tables: `@tanstack/react-table` for Order Book and Positions

Production build for web UI:
```bash
cd web
npm run build
npm start
```

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

### Project structure
```
algorithmic-trading-sim/
  server/               # FastAPI app
  trading/              # Matching engine, order book, core logic
  scripts/              # Benchmarks and utilities
  web/                  # Next.js dashboard UI (Tailwind + shadcn/ui)
```

### Troubleshooting (web)
- Module not found: `@radix-ui/react-slider`
  - Install in `web/`: `npm i @radix-ui/react-slider`
- Turbopack workspace root warning (multiple lockfiles)
  - `web/next.config.ts` sets `turbopack.root` to the `web` folder
- Hydration mismatch (random data / time-based values)
  - Use deterministic sample data (see seeded RNG in `web/src/app/page.tsx`)
- Invalid HTML nesting (`<div>` inside `<tr>`) causing hydration errors
  - `OrderBook` uses a row background gradient for depth overlay instead of nested divs
- React warning: unrecognized `viewportRef` prop
  - `ui/scroll-area` defines a `viewportRef` that is passed to the Radix viewport (not DOM)
- Color parsing error (unsupported LAB/OKLCH in chart library)
  - Use `--chart-text-color` hex variable and read via `getComputedStyle`
- `chart.addCandlestickSeries is not a function`
  - The chart library is dynamically imported client-side; a safe fallback to line series is in place

### License
MIT — see `LICENSE`.


