'use client';

import { useEffect, useState } from 'react';
import { usePrices } from '@/hooks/usePrices';
import { Card } from '@/components/ui/Card';

export function LiveTicker() {
  const { prices } = usePrices(false, 1000); // Update every second
  const [tickerItems, setTickerItems] = useState<Array<{
    symbol: string;
    bestBuy: { exchange: string; price: number };
    bestSell: { exchange: string; price: number };
    spread: number;
  }>>([]);

  useEffect(() => {
    const items: typeof tickerItems = [];
    
    Object.entries(prices).forEach(([symbol, exchanges]) => {
      let bestBuy = { exchange: '', price: Infinity };
      let bestSell = { exchange: '', price: 0 };
      
      Object.entries(exchanges).forEach(([exchange, data]: [string, any]) => {
        if (data?.ask && data.ask < bestBuy.price) {
          bestBuy = { exchange, price: data.ask };
        }
        if (data?.bid && data.bid > bestSell.price) {
          bestSell = { exchange, price: data.bid };
        }
      });
      
      if (bestBuy.price < Infinity && bestSell.price > 0) {
        const spread = ((bestSell.price - bestBuy.price) / bestBuy.price) * 100;
        items.push({ symbol, bestBuy, bestSell, spread });
      }
    });
    
    setTickerItems(items.sort((a, b) => b.spread - a.spread).slice(0, 10));
  }, [prices]);

  if (tickerItems.length === 0) {
    return null;
  }

  return (
    <Card className="overflow-hidden p-0">
      <div className="relative flex overflow-hidden">
        <div className="flex animate-scroll gap-8 whitespace-nowrap">
          {[...tickerItems, ...tickerItems].map((item, idx) => (
            <div key={`${item.symbol}-${idx}`} className="flex items-center gap-4 px-4 py-3">
              <div className="font-semibold text-slate-200">{item.symbol}</div>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-emerald-400">
                  {item.bestBuy.exchange}: ${item.bestBuy.price.toFixed(4)}
                </span>
                <span className="text-slate-500">→</span>
                <span className="text-rose-400">
                  {item.bestSell.exchange}: ${item.bestSell.price.toFixed(4)}
                </span>
              </div>
              <div className={`font-bold ${
                item.spread > 1 ? 'text-emerald-300' : 
                item.spread > 0.5 ? 'text-emerald-400' : 
                'text-slate-400'
              }`}>
                {item.spread.toFixed(2)}%
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

