'use client';

import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { useOpportunities } from '@/hooks/useOpportunities';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import OpportunityChart from '@/components/OpportunityChart';
import OpportunityDistributionChart from '@/components/OpportunityDistributionChart';
import ExchangePairChart from '@/components/ExchangePairChart';

export default function OpportunitiesPage() {
  const { opportunities, isLoading } = useOpportunities(5000);

  // Prepare chart data
  const profitTrendData = opportunities
    .slice()
    .reverse()
    .map((opp) => ({
      time: opp.timestamp,
      profit_percent: opp.profit_percent,
      symbol: opp.symbol,
    }))
    .slice(0, 100);

  // Group by symbol
  const symbolGroups = opportunities.reduce((acc, opp) => {
    if (!acc[opp.symbol]) {
      acc[opp.symbol] = { count: 0, total_profit: 0 };
    }
    acc[opp.symbol].count++;
    acc[opp.symbol].total_profit += opp.profit_percent;
    return acc;
  }, {} as Record<string, { count: number; total_profit: number }>);

  const distributionData = Object.entries(symbolGroups)
    .map(([symbol, data]) => ({
      symbol,
      count: data.count,
      avg_profit: data.total_profit / data.count,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  // Group by exchange pair
  const pairGroups = opportunities.reduce((acc, opp) => {
    const pair = `${opp.buy_exchange} → ${opp.sell_exchange}`;
    if (!acc[pair]) {
      acc[pair] = { count: 0, total_profit: 0 };
    }
    acc[pair].count++;
    acc[pair].total_profit += opp.profit_percent;
    return acc;
  }, {} as Record<string, { count: number; total_profit: number }>);

  const pairData = Object.entries(pairGroups)
    .map(([pair, data]) => ({
      pair,
      count: data.count,
      avg_profit: data.total_profit / data.count,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  const totalOpportunities = opportunities.length;
  const avgProfit = totalOpportunities > 0
    ? opportunities.reduce((sum, opp) => sum + opp.profit_percent, 0) / totalOpportunities
    : 0;
  const maxProfit = opportunities.length > 0
    ? Math.max(...opportunities.map((opp) => opp.profit_percent))
    : 0;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Info Box */}
        <Card variant="elevated" className="border-emerald-500/30 bg-emerald-500/10">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <span className="text-lg">💡</span>
              <div className="flex-1">
                <h4 className="mb-1 text-xs font-semibold text-emerald-200">
                  How Arbitrage Trading Works:
                </h4>
                <p className="text-[11px] text-emerald-100/90">
                  The bot <strong>BUYS</strong> from the exchange with the <strong>lowest price</strong> and <strong>SELLS</strong> to the exchange with the <strong>highest price</strong>.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Total Opportunities</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-100">{totalOpportunities}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Average Profit</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-emerald-400">
                {avgProfit.toFixed(2)}%
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Max Profit</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-emerald-300">
                {maxProfit.toFixed(2)}%
              </div>
            </CardContent>
          </Card>
        </div>

        {isLoading && opportunities.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-slate-400">
              Loading opportunities...
            </CardContent>
          </Card>
        ) : !opportunities.length ? (
          <Card>
            <CardContent className="py-12 text-center text-slate-400">
              No arbitrage opportunities found yet. Let the bot run for a while.
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Charts */}
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Profit Trend Over Time</CardTitle>
                </CardHeader>
                <CardContent>
                  <OpportunityChart
                    data={profitTrendData}
                    title="Profit Trend Over Time"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Opportunities by Symbol</CardTitle>
                </CardHeader>
                <CardContent>
                  <OpportunityDistributionChart
                    data={distributionData}
                    title="Opportunities by Symbol"
                  />
                </CardContent>
              </Card>

              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Top Exchange Pairs (Buy → Sell)</CardTitle>
                </CardHeader>
                <CardContent>
                  <ExchangePairChart
                    data={pairData}
                    title="Top Exchange Pairs (Buy → Sell)"
                  />
                </CardContent>
              </Card>
            </div>

            {/* Opportunities Table */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Opportunities ({opportunities.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-800 text-sm">
                    <thead className="bg-slate-900/80">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Time</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Symbol</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Buy From</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Sell To</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Buy Price</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Sell Price</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Profit %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {opportunities.slice(0, 20).map((opp, idx) => {
                        const profitClass =
                          opp.profit_percent >= 1
                            ? 'text-emerald-300 font-semibold'
                            : opp.profit_percent >= 0.5
                            ? 'text-emerald-400'
                            : 'text-slate-200';
                        return (
                          <tr key={`${opp.symbol}-${opp.timestamp}-${idx}`} className="hover:bg-slate-900/60">
                            <td className="px-3 py-2 text-xs text-slate-300" suppressHydrationWarning>
                              {new Date(opp.timestamp).toLocaleTimeString()}
                            </td>
                            <td className="px-3 py-2 font-semibold text-slate-200">{opp.symbol}</td>
                            <td className="px-3 py-2 text-emerald-300">{opp.buy_exchange}</td>
                            <td className="px-3 py-2 text-rose-300">{opp.sell_exchange}</td>
                            <td className="px-3 py-2 tabular-nums text-slate-300">${opp.buy_price.toFixed(4)}</td>
                            <td className="px-3 py-2 tabular-nums text-slate-300">${opp.sell_price.toFixed(4)}</td>
                            <td className={`px-3 py-2 tabular-nums ${profitClass}`}>
                              {opp.profit_percent < 0.1
                                ? opp.profit_percent.toFixed(4)
                                : opp.profit_percent.toFixed(2)}%
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {opportunities.length > 20 && (
                  <p className="mt-3 text-xs text-slate-400">
                    Showing 20 most recent opportunities. Total: {opportunities.length}
                  </p>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}

