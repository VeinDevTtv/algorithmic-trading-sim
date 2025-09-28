"use client";

import * as React from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

export type Trade = {
  id: string;
  price: number;
  size: number;
  side: "buy" | "sell";
  ts: number;
};

export function RecentTrades({ trades }: { trades: Trade[] }): JSX.Element {
  const parentRef = React.useRef<HTMLDivElement | null>(null);
  const rowVirtualizer = useVirtualizer({
    count: trades.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 36,
    overscan: 8,
  });

  return (
    <ScrollArea className="h-64" viewportRef={parentRef as any}>
      <div style={{ height: rowVirtualizer.getTotalSize(), position: "relative" }}>
        {rowVirtualizer.getVirtualItems().map((virtualRow) => {
          const t = trades[virtualRow.index]!;
          return (
            <div
              key={t.id}
              className="absolute left-0 right-0 px-4"
              style={{ transform: `translateY(${virtualRow.start}px)`, height: virtualRow.size }}
            >
              <div className="flex h-9 items-center justify-between rounded-md border px-3 text-sm">
                <div className="flex items-center gap-2">
                  <Badge variant={t.side === "buy" ? "default" : "destructive"}>{t.side === "buy" ? "Buy" : "Sell"}</Badge>
                  <span className={cn("tabular-nums font-semibold", t.side === "buy" ? "text-emerald-500" : "text-red-500")}>{t.price.toFixed(2)}</span>
                </div>
                <span className="tabular-nums text-muted-foreground">{t.size.toFixed(4)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}


