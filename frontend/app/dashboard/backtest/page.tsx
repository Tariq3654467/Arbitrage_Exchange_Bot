'use client';

import { useState } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { backtestApi, BacktestResult } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export default function BacktestPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<BacktestResult | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [initialCapital, setInitialCapital] = useState('10000');
  const [minProfit, setMinProfit] = useState('');

  // Set default dates (last 30 days)
  useState(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    setEndDate(end.toISOString().split('T')[0]);
    setStartDate(start.toISOString().split('T')[0]);
  });

  const handleRunBacktest = async () => {
    if (!startDate || !endDate) {
      alert('Please select start and end dates');
      return;
    }

    try {
      setIsRunning(true);
      const result = await backtestApi.runBacktest(
        startDate,
        endDate,
        parseFloat(initialCapital) || 10000,
        minProfit ? parseFloat(minProfit) : undefined
      );
      setResults(result);
    } catch (err: any) {
      alert(`Error running backtest: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Backtesting</h1>
          <p className="text-sm text-slate-400 mt-1">
            Test trading strategies on historical data
          </p>
        </div>

        {/* Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Backtest Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  End Date
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Initial Capital (USD)
                </label>
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(e.target.value)}
                  min="100"
                  step="100"
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Min Profit % (Optional)
                </label>
                <input
                  type="number"
                  value={minProfit}
                  onChange={(e) => setMinProfit(e.target.value)}
                  min="0"
                  step="0.1"
                  placeholder="0.5"
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                />
              </div>
            </div>
            <div className="mt-4">
              <Button
                onClick={handleRunBacktest}
                disabled={isRunning}
                className="bg-primary-500 hover:bg-primary-600"
              >
                {isRunning ? 'Running Backtest...' : '▶️ Run Backtest'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Results */}
        {results && (
          <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold text-emerald-400">
                    {results.total_return.toFixed(2)}%
                  </div>
                  <div className="text-sm text-slate-400">Total Return</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold text-slate-100">
                    ${results.final_capital.toLocaleString()}
                  </div>
                  <div className="text-sm text-slate-400">Final Capital</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold text-slate-100">
                    {results.total_trades}
                  </div>
                  <div className="text-sm text-slate-400">Total Trades</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold text-emerald-400">
                    {results.win_rate.toFixed(1)}%
                  </div>
                  <div className="text-sm text-slate-400">Win Rate</div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Detailed Results</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  <div>
                    <div className="text-sm text-slate-400">Winning Trades</div>
                    <div className="text-xl font-bold text-emerald-400">{results.winning_trades}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400">Losing Trades</div>
                    <div className="text-xl font-bold text-rose-400">{results.losing_trades}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400">Max Drawdown</div>
                    <div className="text-xl font-bold text-slate-100">{results.max_drawdown.toFixed(2)}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400">Sharpe Ratio</div>
                    <div className="text-xl font-bold text-slate-100">{results.sharpe_ratio.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400">Initial Capital</div>
                    <div className="text-xl font-bold text-slate-100">${results.initial_capital.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400">Profit</div>
                    <div className="text-xl font-bold text-emerald-400">
                      ${(results.final_capital - results.initial_capital).toLocaleString()}
                    </div>
                  </div>
                </div>
                {results.message && (
                  <div className="mt-4 p-3 rounded-lg bg-amber-500/20 border border-amber-500/40">
                    <p className="text-sm text-amber-200">{results.message}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}

        {/* Info */}
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-slate-400">
              <p className="mb-2">
                <strong className="text-slate-300">Note:</strong> The backtesting engine is currently in development.
                Results shown are simulated and may not reflect actual trading performance.
              </p>
              <p>
                Backtesting uses historical price data to simulate trades based on your strategy parameters.
                Use this to validate strategies before deploying with real capital.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

