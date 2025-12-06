'use client';

import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { tradesApi, Trade } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [filteredTrades, setFilteredTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [tradeStats, setTradeStats] = useState<any>(null);
  const [filterSymbol, setFilterSymbol] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterMinProfit, setFilterMinProfit] = useState('');

  useEffect(() => {
    const loadTrades = async () => {
      try {
        setIsLoading(true);
        const [history, stats] = await Promise.allSettled([
          tradesApi.getHistory(50),
          tradesApi.getStatistics()
        ]);

        if (history.status === 'fulfilled') {
          const allTrades = history.value.trades || [];
          setTrades(allTrades);
          setFilteredTrades(allTrades);
        }
        if (stats.status === 'fulfilled' && !('error' in stats.value)) {
          setTradeStats(stats.value);
        }
      } catch (err) {
        console.error('Error loading trades:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadTrades();
    const interval = setInterval(loadTrades, 5000);
    return () => clearInterval(interval);
  }, []);

  // Apply filters
  useEffect(() => {
    let filtered = [...trades];
    
    if (filterSymbol) {
      filtered = filtered.filter(t => 
        t.symbol.toLowerCase().includes(filterSymbol.toLowerCase())
      );
    }
    
    if (filterStatus !== 'all') {
      filtered = filtered.filter(t => t.status === filterStatus);
    }
    
    if (filterMinProfit) {
      const minProfit = parseFloat(filterMinProfit);
      if (!isNaN(minProfit)) {
        filtered = filtered.filter(t => t.profit_percent >= minProfit);
      }
    }
    
    setFilteredTrades(filtered);
  }, [trades, filterSymbol, filterStatus, filterMinProfit]);

  const handleExport = () => {
    const csv = [
      ['Time', 'Symbol', 'Buy Exchange', 'Sell Exchange', 'Amount', 'Profit USD', 'Profit %', 'Status'].join(','),
      ...filteredTrades.map(t => [
        new Date(t.timestamp).toISOString(),
        t.symbol,
        t.buy_exchange,
        t.sell_exchange,
        t.amount,
        t.profit_usd,
        t.profit_percent,
        t.status
      ].join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trades_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Statistics */}
        {tradeStats && (
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader>
                <CardTitle>Total Trades</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-slate-100">{tradeStats.total_trades || 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Success Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-emerald-400">
                  {(tradeStats.success_rate || 0).toFixed(1)}%
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Total Profit</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-emerald-300">
                  ${(tradeStats.total_profit_usd || 0).toFixed(2)}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Avg Profit %</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-slate-100">
                  {(tradeStats.average_profit_percent || 0).toFixed(2)}%
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Trades Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Trade History</CardTitle>
              <Button
                onClick={handleExport}
                disabled={filteredTrades.length === 0}
                className="text-xs"
                variant="secondary"
              >
                📥 Export CSV
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {/* Filters */}
            <div className="mb-4 grid gap-4 md:grid-cols-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Filter by Symbol</label>
                <input
                  type="text"
                  value={filterSymbol}
                  onChange={(e) => setFilterSymbol(e.target.value)}
                  placeholder="BTC/FDUSD or GALA/USDT"
                  className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-100"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Filter by Status</label>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-100"
                >
                  <option value="all">All</option>
                  <option value="completed">Completed</option>
                  <option value="pending">Pending</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Min Profit %</label>
                <input
                  type="number"
                  value={filterMinProfit}
                  onChange={(e) => setFilterMinProfit(e.target.value)}
                  placeholder="0.5"
                  step="0.1"
                  className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-100"
                />
              </div>
              <div className="flex items-end">
                <Button
                  onClick={() => {
                    setFilterSymbol('');
                    setFilterStatus('all');
                    setFilterMinProfit('');
                  }}
                  variant="ghost"
                  className="w-full text-xs"
                >
                  Clear Filters
                </Button>
              </div>
            </div>
            
            <div className="mb-2 text-xs text-slate-400">
              Showing {filteredTrades.length} of {trades.length} trades
            </div>
            {isLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} variant="rectangular" height={48} />
                ))}
              </div>
            ) : !trades.length ? (
              <div className="py-12 text-center text-slate-400">
                No trades executed yet. Opportunities that meet your thresholds will show here.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-800 text-sm">
                  <thead className="bg-slate-900/80">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Time</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Symbol</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Buy From</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Sell To</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Amount</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Profit (USD)</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Profit %</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {filteredTrades.map((t) => {
                      const profitClass = t.profit_usd >= 0 ? 'text-emerald-300' : 'text-rose-300';
                      return (
                        <tr key={`${t.symbol}-${t.timestamp}`} className="hover:bg-slate-900/60">
                          <td className="px-3 py-2 text-xs text-slate-300" suppressHydrationWarning>
                            {new Date(t.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="px-3 py-2 font-semibold text-slate-200">{t.symbol}</td>
                          <td className="px-3 py-2 text-emerald-300">{t.buy_exchange}</td>
                          <td className="px-3 py-2 text-rose-300">{t.sell_exchange}</td>
                          <td className="px-3 py-2 tabular-nums text-slate-300">{t.amount.toFixed(6)}</td>
                          <td className={`px-3 py-2 tabular-nums ${profitClass}`}>
                            ${t.profit_usd.toFixed(2)}
                          </td>
                          <td className={`px-3 py-2 tabular-nums ${profitClass}`}>
                            {t.profit_percent.toFixed(2)}%
                          </td>
                          <td className="px-3 py-2">
                            <Badge
                              variant={
                                t.status === 'completed' ? 'success' :
                                t.status === 'failed' ? 'error' : 'default'
                              }
                              size="sm"
                            >
                              {t.status}
                            </Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

