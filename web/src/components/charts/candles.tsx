"use client";

import * as React from "react";
import { createChart, IChartApi, ISeriesApi } from "lightweight-charts";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export type Candle = { time: number; open: number; high: number; low: number; close: number; volume: number };
type Interval = "1m" | "5m" | "15m";

export function Candles({ data, onIntervalChange }: { data: Candle[]; onIntervalChange?: (i: Interval) => void }): JSX.Element {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const chartRef = React.useRef<IChartApi | null>(null);
  const seriesRef = React.useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [interval, setInterval] = React.useState<Interval>("1m");

  React.useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "transparent" }, textColor: "var(--color-muted-foreground)" },
      grid: { vertLines: { color: "#2223" }, horzLines: { color: "#2223" } },
      width: containerRef.current.clientWidth,
      height: 360,
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    const s = chart.addCandlestickSeries({ upColor: "#22c55e", downColor: "#ef4444", borderVisible: false });
    s.setData(data.map((c) => ({ time: c.time as any, open: c.open, high: c.high, low: c.low, close: c.close })));
    chartRef.current = chart;
    seriesRef.current = s;
    const ro = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);
    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [data]);

  return (
    <div className="p-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Interval</span>
        <Select
          value={interval}
          onValueChange={(v: Interval) => {
            setInterval(v);
            onIntervalChange?.(v);
          }}
        >
          <SelectTrigger className="h-8 w-[100px]">
            <SelectValue placeholder="1m" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1m">1m</SelectItem>
            <SelectItem value="5m">5m</SelectItem>
            <SelectItem value="15m">15m</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div ref={containerRef} className="w-full" aria-label="Candlestick chart" />
    </div>
  );
}


