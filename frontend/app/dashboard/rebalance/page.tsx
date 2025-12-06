'use client';

import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { rebalanceApi, Allocation } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export default function RebalancePage() {
  const [allocation, setAllocation] = useState<Allocation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRebalancing, setIsRebalancing] = useState(false);
  const [targetAllocation, setTargetAllocation] = useState<Record<string, number>>({});

  useEffect(() => {
    loadAllocation();
    const interval = setInterval(loadAllocation, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadAllocation = async () => {
    try {
      const data = await rebalanceApi.getAllocation();
      setAllocation(data);
      if (Object.keys(targetAllocation).length === 0) {
        setTargetAllocation(data.target || {});
      }
    } catch (err: any) {
      console.error('Error loading allocation:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRebalance = async () => {
    if (!confirm('Trigger manual rebalancing? This will execute transfers to match target allocation.')) {
      return;
    }

    try {
      setIsRebalancing(true);
      const result = await rebalanceApi.triggerRebalance(
        Object.keys(targetAllocation).length > 0 ? targetAllocation : undefined
      );
      alert(`Rebalancing ${result.rebalanced ? 'completed' : 'not needed'}`);
      await loadAllocation();
    } catch (err: any) {
      alert(`Error: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setIsRebalancing(false);
    }
  };

  const handleUpdateAllocation = async () => {
    const total = Object.values(targetAllocation).reduce((sum, val) => sum + val, 0);
    if (Math.abs(total - 100) > 1) {
      alert(`Allocation must sum to ~100% (currently ${total.toFixed(1)}%)`);
      return;
    }

    try {
      await rebalanceApi.updateAllocation(targetAllocation);
      alert('Target allocation updated successfully');
      await loadAllocation();
    } catch (err: any) {
      alert(`Error: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const updateAllocationValue = (asset: string, value: number) => {
    setTargetAllocation({ ...targetAllocation, [asset]: value });
  };

  const allAssets = new Set<string>();
  if (allocation) {
    Object.keys(allocation.current || {}).forEach(a => allAssets.add(a));
    Object.keys(allocation.target || {}).forEach(a => allAssets.add(a));
  }

  const totalTarget = Object.values(targetAllocation).reduce((sum, val) => sum + val, 0);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Portfolio Rebalancing</h1>
            <p className="text-sm text-slate-400 mt-1">
              Manage capital allocation across exchanges and assets
            </p>
          </div>
          <Button
            onClick={handleRebalance}
            disabled={isRebalancing}
            className="bg-primary-500 hover:bg-primary-600"
          >
            {isRebalancing ? 'Rebalancing...' : '🔄 Trigger Rebalance'}
          </Button>
        </div>

        {/* Status Card */}
        {allocation && (
          <Card>
            <CardHeader>
              <CardTitle>Rebalancing Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <Badge variant={allocation.rebalance_needed ? 'warning' : 'success'}>
                  {allocation.rebalance_needed ? 'Rebalancing Needed' : 'Balanced'}
                </Badge>
                {allocation.threshold && (
                  <span className="text-sm text-slate-400">
                    Threshold: {allocation.threshold}%
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Current Allocation */}
          <Card>
            <CardHeader>
              <CardTitle>Current Allocation</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="py-8 text-center text-slate-400">Loading...</div>
              ) : allocation && Object.keys(allocation.current || {}).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(allocation.current).map(([asset, percent]) => (
                    <div key={asset}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-slate-300">{asset}</span>
                        <span className="text-sm text-slate-400">{percent.toFixed(2)}%</span>
                      </div>
                      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary-500 transition-all"
                          style={{ width: `${Math.min(percent, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-slate-400">No allocation data</div>
              )}
            </CardContent>
          </Card>

          {/* Target Allocation */}
          <Card>
            <CardHeader>
              <CardTitle>Target Allocation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Array.from(allAssets).map((asset) => (
                  <div key={asset}>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-slate-300">{asset}</label>
                      <input
                        type="number"
                        value={targetAllocation[asset] || 0}
                        onChange={(e) => updateAllocationValue(asset, parseFloat(e.target.value) || 0)}
                        min="0"
                        max="100"
                        step="0.1"
                        className="w-20 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100 text-right"
                      />
                      <span className="text-sm text-slate-400 w-8">%</span>
                    </div>
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 transition-all"
                        style={{ width: `${Math.min(targetAllocation[asset] || 0, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
                
                {allAssets.size === 0 && (
                  <div className="py-8 text-center text-slate-400">
                    No assets found. Start the bot to see allocation data.
                  </div>
                )}

                <div className="pt-4 border-t border-slate-800">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium text-slate-300">Total</span>
                    <span className={`text-sm font-bold ${
                      Math.abs(totalTarget - 100) < 1 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                      {totalTarget.toFixed(1)}%
                    </span>
                  </div>
                  <Button
                    onClick={handleUpdateAllocation}
                    className="w-full bg-primary-500 hover:bg-primary-600"
                    disabled={Math.abs(totalTarget - 100) > 1}
                  >
                    Update Target Allocation
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}

