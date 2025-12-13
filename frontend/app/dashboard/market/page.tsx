'use client';

import { useState } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { usePrices } from '@/hooks/usePrices';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import PriceChart from '@/components/PriceChart';
import PriceComparisonChart from '@/components/PriceComparisonChart';
import SpreadChart from '@/components/SpreadChart';
import { formatExchangeName } from '@/lib/exchangeUtils';

export default function MarketPage() {
  // Default to showing all pairs to display complete market data
  const [showAllPairs, setShowAllPairs] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const { prices, isLoading, error } = usePrices(showAllPairs, 2000);

  const symbols = Object.keys(prices);
  const currentSymbol = selectedSymbol || symbols[0];
  const exchanges = prices[currentSymbol] as Record<string, any> || {};
  const exchangeNames = Object.keys(exchanges);

  // Prepare comparison data
  const comparisonData = exchangeNames.map((ex) => {
    const data = exchanges[ex];
    return {
      exchange: ex,
      bid: data?.bid || 0,
      ask: data?.ask || 0,
      mid: data?.mid || 0,
    };
  });

  // Build price history (simplified - in production you'd fetch this from API)
  const priceHistory = exchangeNames.map(ex => ({
    time: new Date().toISOString(),
    [`${ex}_mid`]: exchanges[ex]?.mid || 0,
    [`${ex}_bid`]: exchanges[ex]?.bid || 0,
    [`${ex}_ask`]: exchanges[ex]?.ask || 0,
  }));

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Controls */}
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm font-medium text-slate-200 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showAllPairs}
                    onChange={(e) => setShowAllPairs(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-600 bg-slate-900 accent-primary-500"
                  />
                  <span>Show all available market pairs</span>
                </label>
                {symbols.length > 0 && (
                  <Badge variant="info" className="ml-2">
                    {symbols.length} pairs loaded
                  </Badge>
                )}
              </div>
              <div className="text-xs text-slate-400">
                {showAllPairs 
                  ? "Displaying all market data from connected exchanges" 
                  : "Showing only configured trading pairs"}
              </div>
            </div>
          </CardContent>
        </Card>

        {isLoading && symbols.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-slate-400">Loading market data...</div>
          </div>
        ) : error ? (
          <Card>
            <CardContent className="py-12 text-center">
              <div className="text-red-400 font-medium mb-2">Error loading market data</div>
              <div className="text-slate-400 text-sm">{error}</div>
              {error.includes('Bot not running') && (
                <div className="mt-4 text-slate-500 text-xs">
                  Please start the bot from the Dashboard page first.
                </div>
              )}
              {error.includes('No exchanges connected') && (
                <div className="mt-4 text-slate-500 text-xs">
                  Please configure and connect exchanges from the Settings page.
                </div>
              )}
            </CardContent>
          </Card>
        ) : !symbols.length ? (
          <Card>
            <CardContent className="py-12 text-center text-slate-400">
              No market data available yet. Ensure the bot is running and exchanges are connected.
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Symbol selector */}
            <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto">
              {symbols.map((symbol) => (
                <button
                  key={symbol}
                  onClick={() => setSelectedSymbol(symbol)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    selectedSymbol === symbol
                      ? 'bg-primary-500 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {symbol}
                </button>
              ))}
            </div>

            {/* Charts */}
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Mid Price Trend: {currentSymbol}</CardTitle>
                </CardHeader>
                <CardContent>
                  <PriceChart
                    data={priceHistory}
                    exchanges={exchangeNames}
                    dataKey="mid"
                    title={`Mid Price Trend: ${currentSymbol}`}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Price Comparison: {currentSymbol}</CardTitle>
                </CardHeader>
                <CardContent>
                  <PriceComparisonChart data={comparisonData} symbol={currentSymbol} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Bid Price Trend: {currentSymbol}</CardTitle>
                </CardHeader>
                <CardContent>
                  <PriceChart
                    data={priceHistory}
                    exchanges={exchangeNames}
                    dataKey="bid"
                    title={`Bid Price Trend: ${currentSymbol}`}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Spread Trend: {currentSymbol}</CardTitle>
                </CardHeader>
                <CardContent>
                  <SpreadChart
                    data={priceHistory}
                    exchanges={exchangeNames}
                    title={`Spread Trend: ${currentSymbol}`}
                  />
                </CardContent>
              </Card>
            </div>

            {/* Current Prices Table */}
            <Card>
              <CardHeader>
                <CardTitle>Current Prices: {currentSymbol}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-xs">
                  {Object.entries(exchanges).map(([ex, data]) => {
                    const bid = data?.bid?.toFixed(4) || '—';
                    const ask = data?.ask?.toFixed(4) || '—';
                    const mid = data?.mid?.toFixed(4) || '—';
                    const spread = data?.spread?.toFixed(4) || '—';
                    return (
                      <div
                        key={ex}
                        className="flex items-center justify-between rounded-md bg-slate-900/80 px-3 py-2"
                      >
                        <span className="font-medium text-slate-200">{formatExchangeName(ex)}</span>
                        <div className="flex gap-4 tabular-nums text-slate-300">
                          <span>Bid: ${bid}</span>
                          <span>Ask: ${ask}</span>
                          <span>Mid: ${mid}</span>
                          <span>Spread: ${spread}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}

