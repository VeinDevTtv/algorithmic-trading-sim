Algorithmic Trading Simulator - Market Simulation & Visualization

Quick start

1. Create venv and install deps:

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -e .
```

2. Run the server:

```bash
uvicorn server.app:app --reload --port 8000
```

3. Open the UI:

Visit http://localhost:8000 to see order book, trades, and candles.

Notes

- Bots continuously place random limit orders to provide flow.
- Endpoints:
  - GET /api/depth → top-of-book depth
  - GET /api/trades → recent trades
  - GET /api/candles → recent 1m candles


