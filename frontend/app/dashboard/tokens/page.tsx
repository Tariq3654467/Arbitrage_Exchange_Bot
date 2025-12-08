'use client';

import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { tokensApi, TradingPair } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export default function TokensPage() {
  const [pairs, setPairs] = useState<TradingPair[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [newMinAmount, setNewMinAmount] = useState('0.001');
  const [editingSymbol, setEditingSymbol] = useState<string | null>(null);

  useEffect(() => {
    loadPairs();
  }, []);

  const loadPairs = async () => {
    try {
      setIsLoading(true);
      const data = await tokensApi.getPairs();
      setPairs(data || []);
    } catch (err: any) {
      console.error('Error loading trading pairs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!newSymbol || !newMinAmount) {
      alert('Please fill in all fields');
      return;
    }

    try {
      await tokensApi.addPair(newSymbol, parseFloat(newMinAmount), true);
      setNewSymbol('');
      setNewMinAmount('0.001');
      setShowAddForm(false);
      await loadPairs();
    } catch (err: any) {
      alert(`Error adding pair: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const handleDelete = async (symbol: string) => {
    if (!confirm(`Delete trading pair ${symbol}?`)) return;

    try {
      await tokensApi.deletePair(symbol);
      await loadPairs();
    } catch (err: any) {
      alert(`Error deleting pair: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const handleToggle = async (pair: TradingPair) => {
    try {
      await tokensApi.updatePair(pair.symbol, pair.min_trade_amount, !pair.enabled);
      await loadPairs();
    } catch (err: any) {
      alert(`Error updating pair: ${err?.response?.data?.detail || err.message}`);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Token List Management</h1>
            <p className="text-sm text-slate-400 mt-1">
              Manage trading pairs the bot monitors for arbitrage opportunities
            </p>
          </div>
          <Button
            onClick={() => setShowAddForm(!showAddForm)}
            className="bg-primary-500 hover:bg-primary-600"
          >
            {showAddForm ? 'Cancel' : '+ Add Token Pair'}
          </Button>
        </div>

        {/* Add Form */}
        {showAddForm && (
          <Card>
            <CardHeader>
              <CardTitle>Add New Trading Pair</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Symbol (e.g., BTC/FDUSD, ETH/FDUSD, GALA/USDT)
                  </label>
                  <input
                    type="text"
                    value={newSymbol}
                    onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                    placeholder="BTC/FDUSD"
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 outline-none ring-primary-500/40 focus:ring"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Binance supports FDUSD pairs (BTC/FDUSD, ETH/FDUSD) and USDT pairs (GALA/USDT)
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Minimum Trade Amount
                  </label>
                  <input
                    type="number"
                    value={newMinAmount}
                    onChange={(e) => setNewMinAmount(e.target.value)}
                    placeholder="0.001"
                    step="0.000001"
                    min="0"
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 outline-none ring-primary-500/40 focus:ring"
                  />
                </div>
                <Button onClick={handleAdd} className="w-full bg-primary-500 hover:bg-primary-600">
                  Add Trading Pair
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-slate-100">{pairs.length}</div>
              <div className="text-sm text-slate-400">Total Pairs</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-emerald-400">
                {pairs.filter(p => p.enabled).length}
              </div>
              <div className="text-sm text-slate-400">Enabled</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-slate-400">
                {pairs.filter(p => !p.enabled).length}
              </div>
              <div className="text-sm text-slate-400">Disabled</div>
            </CardContent>
          </Card>
        </div>

        {/* Trading Pairs Table */}
        <Card>
          <CardHeader>
            <CardTitle>Configured Trading Pairs</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="py-12 text-center text-slate-400">Loading trading pairs...</div>
            ) : pairs.length === 0 ? (
              <div className="py-12 text-center text-slate-400">
                No trading pairs configured. Add your first pair above.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-800 text-sm">
                  <thead className="bg-slate-900/80">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-400">
                        Symbol
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-400">
                        Min Trade Amount
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-400">
                        Status
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-slate-400">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {pairs.map((pair) => (
                      <tr key={pair.symbol} className="hover:bg-slate-900/60">
                        <td className="px-4 py-3 font-semibold text-slate-200">{pair.symbol}</td>
                        <td className="px-4 py-3 text-slate-300">{pair.min_trade_amount}</td>
                        <td className="px-4 py-3">
                          <Badge variant={pair.enabled ? 'success' : 'default'}>
                            {pair.enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              onClick={() => handleToggle(pair)}
                              className={`text-xs px-3 py-1 ${
                                pair.enabled ? 'bg-amber-600 hover:bg-amber-700' : 'bg-emerald-600 hover:bg-emerald-700'
                              }`}
                            >
                              {pair.enabled ? 'Disable' : 'Enable'}
                            </Button>
                            <Button
                              onClick={() => handleDelete(pair.symbol)}
                              className="text-xs px-3 py-1 bg-rose-600 hover:bg-rose-700"
                            >
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
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

