"use client";

import * as React from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export type Position = { symbol: string; qty: number; avgPrice: number; pnl: number };

export function Positions({ data }: { data: Position[] }): JSX.Element {
  return (
    <div className="p-4">
      <div className="mb-3 text-sm text-muted-foreground">Portfolio / Positions</div>
      <Table aria-label="Positions table">
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Qty</TableHead>
            <TableHead>Avg Price</TableHead>
            <TableHead>PnL</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((p) => (
            <TableRow key={p.symbol}>
              <TableCell className="font-medium">{p.symbol}</TableCell>
              <TableCell className="tabular-nums">{p.qty}</TableCell>
              <TableCell className="tabular-nums">{p.avgPrice.toFixed(2)}</TableCell>
              <TableCell className={`tabular-nums ${p.pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>{p.pnl.toFixed(2)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}


