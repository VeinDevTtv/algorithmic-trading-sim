"use client";

import * as React from "react";
import { ColumnDef, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type OrderBookRow = {
  price: number;
  size: number;
  total: number;
  side: "bid" | "ask";
  depth: number; // 0..1
};

const columns: ColumnDef<OrderBookRow>[] = [
  { header: "Price", accessorKey: "price", cell: ({ getValue, row }) => (
    <span className={cn("font-semibold", row.original.side === "bid" ? "text-emerald-500" : "text-red-500")}>{Number(getValue<number>()).toFixed(2)}</span>
  ) },
  { header: "Size", accessorKey: "size", cell: ({ getValue }) => <span className="tabular-nums font-medium">{Number(getValue<number>()).toFixed(4)}</span> },
  { header: "Total", accessorKey: "total", cell: ({ getValue }) => <span className="tabular-nums text-muted-foreground">{Number(getValue<number>()).toFixed(4)}</span> },
];

export function OrderBook({ data }: { data: OrderBookRow[] }): JSX.Element {
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });

  return (
    <div className="relative">
      <Table aria-label="Order book table">
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}</TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => {
            const widthPct = Math.max(0, Math.min(1, row.original.depth)) * 100;
            const overlayColor = row.original.side === "bid" ? "rgba(34,197,94,0.10)" : "rgba(239,68,68,0.10)"; // emerald/red with 10% opacity
            const hoverClass = row.original.side === "bid" ? "hover:bg-emerald-500/5" : "hover:bg-red-500/5";
            return (
              <TableRow
                key={row.id}
                className={cn("relative transition-colors", hoverClass)}
                style={{
                  backgroundImage: `linear-gradient(to left, ${overlayColor} ${widthPct}%, transparent ${widthPct}%)`,
                  backgroundRepeat: "no-repeat",
                }}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id} className="relative">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}


