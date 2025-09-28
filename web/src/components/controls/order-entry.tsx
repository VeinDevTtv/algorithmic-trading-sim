"use client";

import * as React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

export function OrderEntry(): JSX.Element {
  return (
    <div className="p-4">
      <Tabs defaultValue="market">
        <TabsList>
          <TabsTrigger value="market">Market</TabsTrigger>
          <TabsTrigger value="limit">Limit</TabsTrigger>
          <TabsTrigger value="stop">Stop</TabsTrigger>
        </TabsList>
        <TabsContent value="market" className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="market-size">Size</Label>
              <Input id="market-size" type="number" inputMode="decimal" placeholder="0.0" />
            </div>
            <div>
              <Label>Leverage</Label>
              <Slider defaultValue={[25]} max={100} step={1} aria-label="Leverage" />
            </div>
          </div>
          <div className="flex gap-2">
            <Button className="bg-emerald-600 hover:bg-emerald-500">Buy</Button>
            <Button variant="destructive">Sell</Button>
          </div>
        </TabsContent>
        <TabsContent value="limit" className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label htmlFor="limit-price">Price</Label>
              <Input id="limit-price" type="number" inputMode="decimal" placeholder="0.00" />
            </div>
            <div>
              <Label htmlFor="limit-size">Size</Label>
              <Input id="limit-size" type="number" inputMode="decimal" placeholder="0.0" />
            </div>
            <div>
              <Label>Post Only</Label>
              <Slider defaultValue={[0]} max={1} step={1} aria-label="Post Only" />
            </div>
          </div>
          <div className="flex gap-2">
            <Button className="bg-emerald-600 hover:bg-emerald-500">Buy</Button>
            <Button variant="destructive">Sell</Button>
          </div>
        </TabsContent>
        <TabsContent value="stop" className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label htmlFor="stop-price">Stop</Label>
              <Input id="stop-price" type="number" inputMode="decimal" placeholder="0.00" />
            </div>
            <div>
              <Label htmlFor="stop-limit">Limit</Label>
              <Input id="stop-limit" type="number" inputMode="decimal" placeholder="0.00" />
            </div>
            <div>
              <Label htmlFor="stop-size">Size</Label>
              <Input id="stop-size" type="number" inputMode="decimal" placeholder="0.0" />
            </div>
          </div>
          <div className="flex gap-2">
            <Button className="bg-emerald-600 hover:bg-emerald-500">Buy</Button>
            <Button variant="destructive">Sell</Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}


