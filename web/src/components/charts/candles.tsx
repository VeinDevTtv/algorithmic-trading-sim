"use client";

import * as React from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { IChartApi, ISeriesApi } from "lightweight-charts";

export type Candle = { time: number; open: number; high: number; low: number; close: number; volume: number };
type Interval = "1m" | "5m" | "15m";

export function Candles({ data, onIntervalChange }: { data: Candle[]; onIntervalChange?: (i: Interval) => void }): JSX.Element {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const chartRef = React.useRef<IChartApi | null>(null);
  const seriesRef = React.useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [interval, setInterval] = React.useState<Interval>("1m");

  React.useEffect(() => {
    if (!containerRef.current) return;
    let isMounted = true;
    (async () => {
      const { createChart } = await import("lightweight-charts");
      if (!isMounted || !containerRef.current) return;
      const computed = getComputedStyle(document.documentElement);
      const textColor = computed.getPropertyValue("--chart-text-color").trim() || "#9CA3AF"; // fallback gray-400
      const chart = createChart(containerRef.current, {
        layout: { background: { color: "transparent" }, textColor },
        grid: { vertLines: { color: "rgba(34,34,34,0.2)" }, horzLines: { color: "rgba(34,34,34,0.2)" } },
        width: containerRef.current.clientWidth,
        height: 360,
        timeScale: { timeVisible: true, secondsVisible: false },
      });
      const maybeAddCandle = (chart as any).addCandlestickSeries;
      let series: any;
      if (typeof maybeAddCandle === "function") {
        series = maybeAddCandle.call(chart, { upColor: "#22c55e", downColor: "#ef4444", borderVisible: false });
        series.setData(
          data.map((c) => ({ time: c.time as any, open: c.open, high: c.high, low: c.low, close: c.close }))
        );
      } else if (typeof (chart as any).addLineSeries === "function") {
        series = (chart as any).addLineSeries({ color: "#60a5fa" });
        series.setData(data.map((c) => ({ time: c.time as any, value: c.close })));
      } else {
        // Fallback no-op to avoid crashes in unexpected environments
        series = { setData: () => {} };
      }
      chartRef.current = chart;
      seriesRef.current = series as ISeriesApi<any>;
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
    })();
    return () => {
      isMounted = false;
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


