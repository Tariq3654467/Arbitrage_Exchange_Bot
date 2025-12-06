'use client';

import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { portfolioApi, Balance } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';

export default function BalancesPage() {
  const [balances, setBalances] = useState<Record<string, Balance>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadBalances = async () => {
      try {
        setIsLoading(true);
        const data = await portfolioApi.getBalances();
        if (!('error' in data)) {
          setBalances(data.balances || {});
        }
      } catch (err) {
        console.error('Error loading balances:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadBalances();
    const interval = setInterval(loadBalances, 5000);
    return () => clearInterval(interval);
  }, []);

  const assets = Object.keys(balances);
  const totalValue = assets.reduce((sum, asset) => sum + (balances[asset]?.total_value_usd || 0), 0);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Portfolio Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-100">
              ${totalValue.toFixed(2)}
            </div>
            <p className="mt-2 text-sm text-slate-400">
              Total portfolio value across all exchanges
            </p>
          </CardContent>
        </Card>

        {/* Balances Table */}
        <Card>
          <CardHeader>
            <CardTitle>Asset Balances</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} variant="rectangular" height={48} />
                ))}
              </div>
            ) : !assets.length ? (
              <div className="py-12 text-center text-slate-400">
                No balance data yet. Ensure exchanges are configured and the bot is running.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-800 text-sm">
                  <thead className="bg-slate-900/80">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Asset</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Total Amount</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Value (USD)</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-400">Exchange Distribution</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {assets.map((asset) => {
                      const bal = balances[asset];
                      const exchanges = Object.entries(bal.exchanges)
                        .map(([ex, amt]) => `${ex}: ${amt.toFixed(4)}`)
                        .join(', ');
                      return (
                        <tr key={asset} className="hover:bg-slate-900/60">
                          <td className="px-3 py-2 font-semibold text-slate-200">{asset}</td>
                          <td className="px-3 py-2 tabular-nums text-slate-300">{bal.total_amount.toFixed(6)}</td>
                          <td className="px-3 py-2 tabular-nums text-slate-300">
                            ${bal.total_value_usd.toFixed(2)}
                          </td>
                          <td className="px-3 py-2 text-xs text-slate-400">{exchanges}</td>
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

