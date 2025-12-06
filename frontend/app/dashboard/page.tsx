'use client';

import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { useBotStatus } from '@/hooks/useBotStatus';
import { usePrices } from '@/hooks/usePrices';
import { useOpportunities } from '@/hooks/useOpportunities';
import { riskApi, tradesApi, portfolioApi, botApi } from '@/lib/api';
import { KPICard } from '@/components/dashboard/KPICard';
import { ArbitrageTable } from '@/components/dashboard/ArbitrageTable';
import { RiskControlsPanel } from '@/components/dashboard/RiskControlsPanel';
import { Wallet, TrendingUp, Target, CheckCircle2 } from 'lucide-react';

export default function DashboardOverview() {
  const [riskMetrics, setRiskMetrics] = useState<any>(null);
  const [tradeStats, setTradeStats] = useState<any>(null);
  const [balances, setBalances] = useState<any>(null);

  const { status: botStatus } = useBotStatus();
  const { prices } = usePrices(false, 2000);
  const { opportunities } = useOpportunities(5000);

  // Load additional data
  useEffect(() => {
    const loadData = async () => {
      try {
        const [risk, stats, bal] = await Promise.allSettled([
          riskApi.getMetrics(),
          tradesApi.getStatistics(),
          portfolioApi.getBalances()
        ]);
        
        if (risk.status === 'fulfilled' && !('error' in risk.value)) {
          setRiskMetrics(risk.value);
        }
        if (stats.status === 'fulfilled' && !('error' in stats.value)) {
          setTradeStats(stats.value);
        }
        if (bal.status === 'fulfilled' && !('error' in bal.value)) {
          setBalances(bal.value);
        }
      } catch (err) {
        console.error('Error loading dashboard data:', err);
      }
    };

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Calculate portfolio value
  const portfolioValue = balances?.balances
    ? Object.values(balances.balances).reduce((sum: number, bal: any) => sum + (bal.total_value_usd || 0), 0)
    : 0;

  // Calculate daily P&L
  const dailyPnL = riskMetrics?.daily_pnl || 0;
  const dailyPnLPercent = riskMetrics?.daily_pnl_percent || 0;

  // Format opportunities for table
  const formattedOpportunities = opportunities.map(opp => ({
    symbol: opp.symbol,
    buy_exchange: opp.buy_exchange,
    sell_exchange: opp.sell_exchange,
    buy_price: opp.buy_price || 0,
    sell_price: opp.sell_price || 0,
    spread: opp.profit_percent || 0,
    profit_percent: opp.profit_percent || 0,
    net_profit: (opp.profit_usd || 0),
    timestamp: opp.timestamp || new Date().toISOString()
  }));

  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  };

  const handleEmergencyStop = async () => {
    const confirmed = window.confirm('🚨 EMERGENCY STOP - Halt all trading?');
    if (!confirmed) return;
    try {
      await botApi.emergencyStop();
      showNotification('Emergency stop activated!', 'success');
    } catch (err: any) {
      showNotification(err?.message || 'Failed to activate emergency stop', 'error');
    }
  };

  const handleUpdateRisk = async (config: any) => {
    try {
      await riskApi.saveRiskConfig(config);
    } catch (err) {
      console.error('Error updating risk config:', err);
    }
  };

  return (
    <DashboardLayout>
      {/* Notification Toast */}
      {notification && (
        <div className={`fixed top-4 right-4 z-50 rounded-lg px-4 py-3 shadow-lg backdrop-blur-sm animate-in slide-in-from-right ${
          notification.type === 'success' ? 'bg-emerald-600/90 text-white' : 'bg-red-600/90 text-white'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{notification.message}</span>
            <button onClick={() => setNotification(null)} className="ml-4 text-white/80 hover:text-white">×</button>
          </div>
        </div>
      )}
      <div className="space-y-6">
        {/* KPI Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            title="Total Portfolio Value"
            value={`$${portfolioValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            change={dailyPnLPercent ? {
              value: dailyPnLPercent,
              isPositive: dailyPnLPercent > 0,
              label: 'today'
            } : undefined}
            icon={<Wallet className="h-8 w-8" />}
            iconColor="text-[#4ade80]"
            isLoading={!balances}
          />
          <KPICard
            title="Daily P&L"
            value={`$${dailyPnL.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            change={dailyPnLPercent ? {
              value: Math.abs(dailyPnLPercent),
              isPositive: dailyPnLPercent > 0,
              label: 'today'
            } : undefined}
            icon={<TrendingUp className="h-8 w-8" />}
            iconColor={dailyPnL >= 0 ? 'text-[#4ade80]' : 'text-[#ef4444]'}
            isLoading={!riskMetrics}
          />
          <KPICard
            title="Active Opportunities"
            value={opportunities.length}
            icon={<Target className="h-8 w-8" />}
            iconColor="text-[#60a5fa]"
          />
          <KPICard
            title="Success Rate"
            value={`${tradeStats?.success_rate?.toFixed(1) || 0}%`}
            icon={<CheckCircle2 className="h-8 w-8" />}
            iconColor="text-[#38bdf8]"
            isLoading={!tradeStats}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Arbitrage Table - Takes 2 columns */}
          <div className="lg:col-span-2">
            <ArbitrageTable 
              opportunities={formattedOpportunities}
              isLoading={false}
            />
          </div>

          {/* Risk Controls Panel - Takes 1 column */}
          <div className="lg:col-span-1">
            <RiskControlsPanel
              riskMetrics={riskMetrics}
              onEmergencyStop={handleEmergencyStop}
              onUpdateRisk={handleUpdateRisk}
            />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
