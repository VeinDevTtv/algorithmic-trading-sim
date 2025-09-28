from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from trading.core import MatchingEngine, OrderBook, OrderFactory, OrderSide, Trader
from trading.analytics.ohlc import CandleAggregator
from trading.sim.bots import BotScheduler, RandomBot


app = FastAPI(title="Algorithmic Trading Simulator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Single-market in-memory instance ---
SYMBOL = "AAPL"
order_book = OrderBook(symbol=SYMBOL)
engine = MatchingEngine(order_book=order_book)
candles = CandleAggregator(symbol=SYMBOL, period_seconds=60)


@engine.subscribe  # type: ignore[attr-defined]
def _(event: str, payload):
    # forward trades to candle aggregator
    if event == "trade_executed":
        candles.add_trade(payload)


def _init_bots() -> BotScheduler:
    # seed two traders with cash and constraints friendly to random orders
    t1 = Trader(trader_id="bot1", balance=1_000_000.0)
    t2 = Trader(trader_id="bot2", balance=1_000_000.0)
    engine.register_trader(t1)
    engine.register_trader(t2)
    # anchor price
    price_anchor = 100.0
    bots = [
        RandomBot(trader=t1, symbol=SYMBOL, price_ref=price_anchor, price_spread=1.5, max_qty=3.0),
        RandomBot(trader=t2, symbol=SYMBOL, price_ref=price_anchor, price_spread=1.5, max_qty=3.0),
    ]
    sched = BotScheduler(engine=engine, bots=bots, min_interval_ms=150, max_interval_ms=600)
    sched.start()
    return sched


scheduler = _init_bots()


async def tick_loop():
    # run scheduler in background
    while True:
        scheduler.run_until(datetime.now(tz=timezone.utc) + timedelta(milliseconds=50))
        await asyncio.sleep(0.05)


@app.on_event("startup")
async def _startup():
    asyncio.create_task(tick_loop())


@app.get("/api/depth")
async def api_depth():
    return order_book.depth(levels=10)


@app.get("/api/trades")
async def api_trades():
    return [
        {
            "buy_order_id": t.buy_order_id,
            "sell_order_id": t.sell_order_id,
            "price": t.price,
            "quantity": t.quantity,
            "timestamp": t.timestamp.isoformat(),
        }
        for t in engine.trades[-200:]
    ]


@app.get("/api/candles")
async def api_candles():
    return [
        {
            "symbol": c.symbol,
            "start": c.start.isoformat(),
            "end": c.end.isoformat(),
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
            "trades": c.trades,
        }
        for c in candles.recent(200)
    ]


@app.get("/")
async def index() -> HTMLResponse:
    # Minimal frontend without build step
    html = """
<!doctype html>
<html>
  <head>
    <meta charset='utf-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1' />
    <title>Market Simulator</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 16px; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
      .card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
      h2 { margin: 0 0 8px; font-size: 16px; }
      table { width: 100%; border-collapse: collapse; }
      th, td { text-align: right; padding: 4px 6px; border-bottom: 1px solid #eee; }
      canvas { width: 100%; height: 240px; }
    </style>
  </head>
  <body>
    <h1>Market Simulator</h1>
    <div class='grid'>
      <div class='card'>
        <h2>Order Book Depth (Top 10)</h2>
        <table><thead><tr><th>Bid Px</th><th>Bid Qty</th><th>Ask Px</th><th>Ask Qty</th></tr></thead>
        <tbody id='depth'></tbody></table>
      </div>
      <div class='card'>
        <h2>Recent Trades</h2>
        <table><thead><tr><th>Time</th><th>Px</th><th>Qty</th></tr></thead>
        <tbody id='trades'></tbody></table>
      </div>
      <div class='card' style='grid-column: span 2;'>
        <h2>OHLC Candles (1m)</h2>
        <canvas id='candles'></canvas>
      </div>
    </div>
    <script>
      const depthBody = document.getElementById('depth');
      const tradesBody = document.getElementById('trades');
      const canvas = document.getElementById('candles');
      const ctx = canvas.getContext('2d');

      async function fetchDepth() {
        const res = await fetch('/api/depth');
        const d = await res.json();
        const rows = [];
        for (let i = 0; i < 10; i++) {
          const b = d.bids[i] || ['', ''];
          const a = d.asks[i] || ['', ''];
          rows.push(`<tr><td>${b[0]??''}</td><td>${b[1]??''}</td><td>${a[0]??''}</td><td>${a[1]??''}</td></tr>`);
        }
        depthBody.innerHTML = rows.join('');
      }

      async function fetchTrades() {
        const res = await fetch('/api/trades');
        const t = await res.json();
        const rows = t.slice(-30).reverse().map(x => `<tr><td>${new Date(x.timestamp).toLocaleTimeString()}</td><td>${x.price.toFixed(2)}</td><td>${x.quantity.toFixed(2)}</td></tr>`);
        tradesBody.innerHTML = rows.join('');
      }

      function drawCandles(candles) {
        const w = canvas.clientWidth, h = canvas.clientHeight;
        canvas.width = w; canvas.height = h;
        ctx.clearRect(0,0,w,h);
        if (candles.length === 0) return;
        const xs = candles.map((_,i)=>i);
        const highs = candles.map(c=>c.high);
        const lows = candles.map(c=>c.low);
        const minP = Math.min(...lows), maxP = Math.max(...highs);
        const pad = (maxP - minP) * 0.05;
        const ymin = minP - pad, ymax = maxP + pad;
        const xstep = w / Math.max(1, candles.length);
        const y = p => h - ( (p - ymin) / (ymax - ymin) ) * h;
        candles.forEach((c, i) => {
          const x = i * xstep + xstep*0.5;
          ctx.strokeStyle = c.close >= c.open ? '#2e7d32' : '#c62828';
          ctx.beginPath();
          ctx.moveTo(x, y(c.high));
          ctx.lineTo(x, y(c.low));
          ctx.stroke();
          const bw = Math.max(2, xstep * 0.6);
          ctx.fillStyle = ctx.strokeStyle;
          const top = y(Math.max(c.open, c.close));
          const bot = y(Math.min(c.open, c.close));
          ctx.fillRect(x - bw/2, top, bw, Math.max(1, bot - top));
        });
      }

      async function fetchCandles() {
        const res = await fetch('/api/candles');
        const c = await res.json();
        drawCandles(c.slice(-120));
      }

      async function loop() {
        await Promise.all([fetchDepth(), fetchTrades(), fetchCandles()]);
        setTimeout(loop, 500);
      }
      loop();
    </script>
  </body>
</html>
    """
    return HTMLResponse(content=html)


