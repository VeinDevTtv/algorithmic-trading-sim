import { OrderBook, type OrderBookRow } from "@/components/orderbook/order-book";
import { RecentTrades, type Trade } from "@/components/trades/recent-trades";
import { Candles, type Candle } from "@/components/charts/candles";
import { OrderEntry } from "@/components/controls/order-entry";
import { Positions, type Position } from "@/components/portfolio/positions";
import { AnimatedNumber } from "@/components/metrics/animated-number";

function seededRandom(seed: number) {
  let t = seed;
  return () => {
    t = (t * 1664525 + 1013904223) % 4294967296;
    return t / 4294967296;
  };
}
const rnd = seededRandom(12345);
const sampleOrderBook: OrderBookRow[] = Array.from({ length: 16 }).map((_, i) => ({
  price: 1000 + i * 0.5,
  size: rnd(),
  total: rnd() * 5,
  side: i % 2 === 0 ? "bid" : "ask",
  depth: rnd(),
}));

const sampleTrades: Trade[] = Array.from({ length: 100 }).map((_, i) => ({
  id: `t${i}`,
  price: 1000 + Math.sin(i / 5) * 5,
  size: rnd(),
  side: i % 2 === 0 ? "buy" : "sell",
  ts: 1700000000000 - i * 60000,
}));

const sampleCandles: Candle[] = Array.from({ length: 100 }).map((_, i) => {
  const base = 1000 + i * 0.2;
  const open = base + rnd() * 2 - 1;
  const close = base + rnd() * 2 - 1;
  const high = Math.max(open, close) + rnd() * 2;
  const low = Math.min(open, close) - rnd() * 2;
  return { time: Math.floor(1700000000000 / 1000) - (100 - i) * 60, open, high, low, close, volume: rnd() * 100 };
});

const samplePositions: Position[] = [
  { symbol: "BTC-USD", qty: 0.12, avgPrice: 985.23, pnl: 12.34 },
  { symbol: "ETH-USD", qty: 1.5, avgPrice: 1823.77, pnl: -5.12 },
];

export default function Page(): JSX.Element {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6">
      <div className="grid grid-cols-1 gap-4 md:gap-6 xl:grid-cols-2">
        <div className="flex flex-col gap-4 md:gap-6">
          <section aria-label="Order book" className="rounded-lg border bg-card text-card-foreground shadow-sm">
            <div className="p-4 font-semibold">Order Book</div>
            <div className="px-4 pb-4">
              <OrderBook data={sampleOrderBook} />
            </div>
          </section>
          <section aria-label="Market depth" className="rounded-lg border bg-card text-card-foreground shadow-sm">
            <div className="p-4 font-semibold">Market Depth</div>
            <div className="px-4 pb-4 text-sm text-muted-foreground">Depth chart</div>
          </section>
        </div>
        <div className="flex flex-col gap-4 md:gap-6">
          <section aria-label="Recent trades" className="rounded-lg border bg-card text-card-foreground shadow-sm">
            <div className="p-4 font-semibold">Recent Trades</div>
            <div className="px-4 pb-4">
              <RecentTrades trades={sampleTrades} />
            </div>
          </section>
          <section aria-label="Portfolio and positions" className="rounded-lg border bg-card text-card-foreground shadow-sm">
            <div className="p-4 font-semibold">PnL / Positions</div>
            <div className="px-4 pb-4">
              <Positions data={samplePositions} />
            </div>
          </section>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 md:mt-6 md:gap-6">
        <section aria-label="Candlestick chart" className="rounded-lg border bg-card text-card-foreground shadow-sm">
          <div className="p-4 font-semibold">Candlesticks & Volume</div>
          <div className="px-4 pb-4">
            <Candles data={sampleCandles} />
          </div>
        </section>
        <section aria-label="Order entry" className="rounded-lg border bg-card text-card-foreground shadow-sm">
          <div className="p-4 font-semibold">Trade Controls</div>
          <div className="px-4 pb-4">
            <OrderEntry />
          </div>
        </section>
        <section aria-label="Summary metrics" className="rounded-lg border bg-card text-card-foreground shadow-sm">
          <div className="p-4 font-semibold">PnL</div>
          <div className="px-4 pb-4 text-2xl font-bold">
            <AnimatedNumber value={samplePositions.reduce((a, b) => a + b.pnl, 0)} className={samplePositions.reduce((a,b)=>a+b.pnl,0) >= 0 ? "text-emerald-500" : "text-red-500"} />
          </div>
        </section>
      </div>
    </div>
  );
}
