/* Main Next.js dashboard page */
'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  botApi,
  BotStatus,
  marketApi,
  Opportunity,
  tradesApi,
  Trade,
  portfolioApi,
  Balance,
  riskApi,
  RiskMetrics,
  TradeStatistics,
  configApi,
  TradingConfig,
  RiskConfig,
  ExchangesResponse,
  ConfiguredExchange,
  EphemeralExchange,
  DEXConfig,
} from '@/lib/api';
import StatusIndicator from '@/components/StatusIndicator';
import { useWebSocket } from '@/lib/useWebSocket';
import PriceChart from '@/components/PriceChart';
import PriceComparisonChart from '@/components/PriceComparisonChart';
import SpreadChart from '@/components/SpreadChart';
import OpportunityChart from '@/components/OpportunityChart';
import OpportunityDistributionChart from '@/components/OpportunityDistributionChart';
import ExchangePairChart from '@/components/ExchangePairChart';

type TabId = 'market' | 'opportunities' | 'trades' | 'balances' | 'config';

interface Alert {
  id: number;
  type: 'success' | 'error' | 'info' | 'critical';
  message: string;
}

export default function DashboardPage() {
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [tradeStats, setTradeStats] = useState<TradeStatistics | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [balances, setBalances] = useState<Record<string, Balance>>({});
  const [activeTab, setActiveTab] = useState<TabId>('market');
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [tradingConfig, setTradingConfig] = useState<TradingConfig | null>(null);
  const [riskConfig, setRiskConfig] = useState<RiskConfig | null>(null);
  const [savingTrading, setSavingTrading] = useState(false);
  const [savingRisk, setSavingRisk] = useState(false);
  const [exchangesConfig, setExchangesConfig] = useState<ExchangesResponse | null>(null);
  const [ephemeralExchanges, setEphemeralExchanges] = useState<EphemeralExchange[]>([]);

  // WebSocket should connect directly to the API server (FastAPI), not the Next.js port.
  // Use the same default as our HTTP API client: http://localhost:8000
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const wsBase = apiBase.replace(/^http/, 'ws');
  const { isConnected: wsConnected, lastMessage } = useWebSocket(`${wsBase}/ws`);

  // Apply WebSocket updates
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'status_update' && lastMessage.data) {
      setBotStatus(lastMessage.data as BotStatus);
    } else if (lastMessage.type === 'bot_status') {
      if (lastMessage.message) {
        pushAlert('info', lastMessage.message);
      }
      if (lastMessage.data) {
        setBotStatus(lastMessage.data as BotStatus);
      }
    } else if (lastMessage.type === 'alert') {
      pushAlert(
        (lastMessage.level as Alert['type']) || 'info',
        lastMessage.message || 'Alert received',
      );
    }
  }, [lastMessage]);

  // Shared loader for initial + background refresh
  const loadDashboard = async (showLoading: boolean) => {
    try {
      if (showLoading) {
        setIsLoading(true);
      }
      const [
        status,
        risk,
        stats,
        opp,
        hist,
        bal,
        tConfig,
        rConfig,
        exch,
      ] = await Promise.allSettled([
        botApi.getStatus(),
        riskApi.getMetrics(),
        tradesApi.getStatistics(),
        marketApi.getOpportunities(),
        tradesApi.getHistory(50),
        portfolioApi.getBalances(),
        configApi.getTradingConfig(),
        configApi.getRiskConfig(),
        configApi.getExchanges(),
      ]);

      if (status.status === 'fulfilled') setBotStatus(status.value);
      if (risk.status === 'fulfilled' && !('error' in risk.value)) {
        setRiskMetrics(risk.value);
      }
      if (stats.status === 'fulfilled' && !('error' in stats.value)) {
        setTradeStats(stats.value);
      }
      if (opp.status === 'fulfilled') {
        setOpportunities(opp.value.opportunities || []);
      }
      if (hist.status === 'fulfilled') {
        setTrades(hist.value.trades || []);
      }
      if (bal.status === 'fulfilled' && !('error' in bal.value)) {
        setBalances(bal.value.balances || {});
      }
      if (tConfig.status === 'fulfilled') setTradingConfig(tConfig.value);
      if (rConfig.status === 'fulfilled') setRiskConfig(rConfig.value);
      if (exch.status === 'fulfilled') setExchangesConfig(exch.value);
    } catch {
      pushAlert('error', 'Failed to load dashboard data');
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  // Initial load once on mount
  useEffect(() => {
    loadDashboard(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Background refresh (disabled while on Config tab so typing API keys is not interrupted)
  useEffect(() => {
    if (activeTab === 'config') {
      return;
    }

    const interval = setInterval(() => {
      loadDashboard(false);
    }, 5000);

    return () => clearInterval(interval);
  }, [activeTab]);

  const pushAlert = (type: Alert['type'], message: string) => {
    setAlerts((prev) => [
      ...prev,
      { id: Date.now() + Math.random(), type, message },
    ]);
    setTimeout(() => {
      setAlerts((prev) => prev.slice(1));
    }, 5000);
  };

  const handleStart = async () => {
    try {
      setIsStarting(true);
      const payload =
        ephemeralExchanges.length > 0 ? { exchanges: ephemeralExchanges } : undefined;
      const res = await botApi.start(payload);
      pushAlert(res.status === 'success' ? 'success' : 'error', res.message);
      const status = await botApi.getStatus();
      setBotStatus(status);
    } catch (e: any) {
      pushAlert('error', e?.message || 'Failed to start bot');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    try {
      setIsStopping(true);
      const res = await botApi.stop();
      pushAlert(res.status === 'success' ? 'success' : 'error', res.message);
      const status = await botApi.getStatus();
      setBotStatus(status);
    } catch (e: any) {
      pushAlert('error', e?.message || 'Failed to stop bot');
    } finally {
      setIsStopping(false);
    }
  };

  const handleEmergencyStop = async () => {
    if (!window.confirm('Trigger EMERGENCY STOP? This will halt all trading immediately.')) {
      return;
    }
    try {
      const res = await botApi.emergencyStop();
      pushAlert(res.status === 'success' ? 'critical' : 'error', res.message);
    } catch (e: any) {
      pushAlert('error', e?.message || 'Failed to trigger emergency stop');
    }
  };

  const formattedUptime = useMemo(() => {
    if (!botStatus?.uptime_seconds) return '00:00:00';
    const s = botStatus.uptime_seconds;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    return [h, m, sec].map((x) => String(x).padStart(2, '0')).join(':');
  }, [botStatus?.uptime_seconds]);

  const handleSaveTrading = async () => {
    if (!tradingConfig) return;
    try {
      setSavingTrading(true);
      const res = await configApi.saveTradingConfig(tradingConfig);
      pushAlert(res.status === 'success' ? 'success' : 'error', res.message || 'Failed to save');
    } catch (e: any) {
      pushAlert('error', e?.message || 'Failed to save trading config');
    } finally {
      setSavingTrading(false);
    }
  };

  const handleSaveRisk = async () => {
    if (!riskConfig) return;
    try {
      setSavingRisk(true);
      const res = await configApi.saveRiskConfig(riskConfig);
      pushAlert(res.status === 'success' ? 'success' : 'error', res.message || 'Failed to save');
    } catch (e: any) {
      pushAlert('error', e?.message || 'Failed to save risk config');
    } finally {
      setSavingRisk(false);
    }
  };

  const handleTogglePaperTrading = async () => {
    if (!botStatus) return;
    const newMode = !botStatus.paper_trading;
    const modeName = newMode ? 'Paper Trading' : 'Live Trading';
    
    if (!newMode && !window.confirm(
      `⚠️ WARNING: Switch to LIVE TRADING?\n\n` +
      `This will use REAL FUNDS. Make sure you understand the risks.\n\n` +
      `The bot will need to be restarted for this change to take effect.`
    )) {
      return;
    }
    
    try {
      const res = await botApi.setTradingMode(newMode);
      pushAlert(
        res.status === 'success' ? 'info' : 'error',
        res.message || `Failed to switch to ${modeName}`
      );
      // Refresh bot status to get updated paper_trading value
      if (res.status === 'success') {
        setTimeout(() => loadDashboard(false), 1000);
      }
    } catch (e: any) {
      pushAlert('error', e?.message || `Failed to switch to ${modeName}`);
    }
  };

  const refreshExchanges = async () => {
    try {
      const data = await configApi.getExchanges();
      setExchangesConfig(data);
    } catch (e) {
      pushAlert('error', 'Failed to refresh exchange list');
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-primary-500 via-slate-900 to-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-6 md:py-10">
        {/* Header */}
        <header className="mb-6 flex flex-col gap-4 rounded-2xl bg-slate-900/80 p-5 shadow-xl ring-1 ring-white/10 backdrop-blur-md md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-2xl">🤖</span>
              <h1 className="text-xl font-semibold tracking-tight md:text-2xl">
                Arbitrage Bot Dashboard
              </h1>
            </div>
            <p className="mt-2 text-sm text-slate-400">
              Monitor markets, manage exchanges, and control your trading bot in real time.
            </p>
          </div>
          <div className="flex flex-col items-start gap-3 md:items-end">
            <StatusIndicator status={botStatus} />
            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span
                className={`flex items-center gap-1 rounded-full px-2 py-1 ${
                  wsConnected ? 'bg-emerald-500/10 text-emerald-300' : 'bg-slate-700/60'
                }`}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                Realtime {wsConnected ? 'connected' : 'disconnected'}
              </span>
              <span>Uptime: {formattedUptime}</span>
            </div>
          </div>
        </header>

        {/* Alerts */}
        <div className="space-y-2">
          {alerts.map((a) => (
            <div
              key={a.id}
              className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm shadow-sm ${
                a.type === 'success'
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100'
                  : a.type === 'error'
                  ? 'border-rose-500/40 bg-rose-500/10 text-rose-100'
                  : a.type === 'critical'
                  ? 'border-red-500/60 bg-red-600/20 text-red-50'
                  : 'border-sky-500/40 bg-sky-500/10 text-sky-100'
              }`}
            >
              <span>{a.message}</span>
            </div>
          ))}
        </div>

        {/* Controls + Metrics */}
        <section className="mt-4 grid gap-5 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          {/* Control panel */}
          <div className="space-y-3 rounded-2xl bg-slate-900/80 p-4 shadow-lg ring-1 ring-white/10">
            <h2 className="mb-1 text-sm font-medium text-slate-200">Bot Controls</h2>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleStart}
                disabled={botStatus?.is_running || isStarting}
                className="inline-flex items-center justify-center rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-emerald-950 shadow hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-emerald-700/60"
              >
                {isStarting ? 'Starting…' : '▶ Start Bot'}
              </button>
              <button
                onClick={handleStop}
                disabled={!botStatus?.is_running || isStopping}
                className="inline-flex items-center justify-center rounded-lg bg-rose-500 px-3 py-2 text-sm font-semibold text-rose-50 shadow hover:bg-rose-400 disabled:cursor-not-allowed disabled:bg-rose-700/60"
              >
                {isStopping ? 'Stopping…' : '⏹ Stop Bot'}
              </button>
              <button
                onClick={handleEmergencyStop}
                className="inline-flex items-center justify-center rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-red-50 shadow-lg shadow-red-500/40 hover:bg-red-500"
              >
                🚨 Emergency Stop
              </button>
            </div>
            
            {/* Trading Mode Controls */}
            {botStatus?.is_running && (
              <div className="mt-4 space-y-2 rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs font-medium text-slate-200">Auto-Trading</div>
                    <div className="text-[10px] text-slate-400">
                      {riskMetrics?.trading_enabled
                        ? 'Bot will automatically execute trades when profitable opportunities are found'
                        : 'Trades are disabled - bot will only monitor opportunities'}
                    </div>
                  </div>
                  <button
                    onClick={async () => {
                      try {
                        if (riskMetrics?.trading_enabled) {
                          await botApi.disableTrading();
                          pushAlert('info', 'Auto-trading disabled');
                        } else {
                          await botApi.enableTrading();
                          pushAlert('success', 'Auto-trading enabled');
                        }
                        // Refresh data
                        const [risk] = await Promise.allSettled([riskApi.getMetrics()]);
                        if (risk.status === 'fulfilled' && !('error' in risk.value)) {
                          setRiskMetrics(risk.value);
                        }
                      } catch (e: any) {
                        pushAlert('error', e?.response?.data?.detail || 'Failed to toggle trading');
                      }
                    }}
                    className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                      riskMetrics?.trading_enabled
                        ? 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {riskMetrics?.trading_enabled ? '✓ Enabled' : 'Disabled'}
                  </button>
                </div>
                <div className="flex items-center justify-between border-t border-slate-800 pt-2">
                  <div>
                    <div className="text-xs font-medium text-slate-200">Trading Mode</div>
                    <div className="text-[10px] text-slate-400">
                      {botStatus.paper_trading
                        ? 'Paper Trading (simulated) - No real funds are used'
                        : 'Live Trading - Real funds will be used'}
                    </div>
                  </div>
                  <button
                    onClick={handleTogglePaperTrading}
                    className={`rounded-md px-2 py-1 text-[10px] font-semibold uppercase transition-colors cursor-pointer ${
                      botStatus.paper_trading
                        ? 'bg-amber-500/20 text-amber-300 hover:bg-amber-500/30'
                        : 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
                    }`}
                    title={`Click to switch to ${botStatus.paper_trading ? 'Live' : 'Paper'} Trading`}
                  >
                    {botStatus.paper_trading ? 'Paper' : 'Live'}
                  </button>
                </div>
              </div>
            )}
            
            <p className="mt-1 text-xs text-slate-500">
              Exchange keys and risk settings are managed from the Configuration tab.
            </p>
          </div>

          {/* Metric cards */}
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard
              title="Portfolio Value"
              value={
                riskMetrics
                  ? `$${(riskMetrics.portfolio_value || 0).toFixed(2)}`
                  : '—'
              }
              subtitle="Across all connected exchanges"
            />
            <MetricCard
              title="Daily P&L"
              value={
                riskMetrics
                  ? `$${(riskMetrics.daily_pnl || 0).toFixed(2)}`
                  : '—'
              }
              subtitle="Realized performance today"
              tone={
                riskMetrics && riskMetrics.daily_pnl < 0
                  ? 'negative'
                  : riskMetrics && riskMetrics.daily_pnl > 0
                  ? 'positive'
                  : 'neutral'
              }
            />
            <MetricCard
              title="Total Trades"
              value={tradeStats ? tradeStats.total_trades.toString() : '0'}
              subtitle={
                tradeStats
                  ? `Win rate ${(tradeStats.success_rate || 0).toFixed(1)}%`
                  : 'Waiting for first trades'
              }
            />
          </div>
        </section>

        {/* Tabs */}
        <section className="mt-6 rounded-2xl bg-slate-950/60 p-1.5 shadow-xl ring-1 ring-white/10">
          <div className="flex flex-wrap gap-1 rounded-xl bg-slate-900/70 p-1">
            <TabButton id="market" activeTab={activeTab} setActiveTab={setActiveTab}>
              📈 Market
            </TabButton>
            <TabButton
              id="opportunities"
              activeTab={activeTab}
              setActiveTab={setActiveTab}
            >
              💰 Opportunities
            </TabButton>
            <TabButton id="trades" activeTab={activeTab} setActiveTab={setActiveTab}>
              📋 Trades
            </TabButton>
            <TabButton
              id="balances"
              activeTab={activeTab}
              setActiveTab={setActiveTab}
            >
              💵 Balances
            </TabButton>
            <TabButton id="config" activeTab={activeTab} setActiveTab={setActiveTab}>
              ⚙ Configuration
            </TabButton>
          </div>

          <div className="mt-3 rounded-xl bg-slate-900/80 p-4 md:p-5">
            {isLoading && (
              <div className="flex flex-col items-center justify-center gap-3 py-10 text-sm text-slate-400">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-primary-400" />
                <span>Loading dashboard data…</span>
              </div>
            )}

            {!isLoading && activeTab === 'market' && <MarketTab />}
            {!isLoading && activeTab === 'opportunities' && (
              <OpportunitiesTab opportunities={opportunities} />
            )}
            {!isLoading && activeTab === 'trades' && <TradesTab trades={trades} />}
            {!isLoading && activeTab === 'balances' && (
              <BalancesTab balances={balances} />
            )}
            {!isLoading && activeTab === 'config' && (
              <ConfigTab
                tradingConfig={tradingConfig}
                setTradingConfig={setTradingConfig}
                riskConfig={riskConfig}
                setRiskConfig={setRiskConfig}
                onSaveTrading={handleSaveTrading}
                onSaveRisk={handleSaveRisk}
                savingTrading={savingTrading}
                savingRisk={savingRisk}
                exchangesConfig={exchangesConfig}
                onRefreshExchanges={refreshExchanges}
                ephemeralExchanges={ephemeralExchanges}
                setEphemeralExchanges={setEphemeralExchanges}
              />
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

function TabButton({
  id,
  activeTab,
  setActiveTab,
  children,
}: {
  id: TabId;
  activeTab: TabId;
  setActiveTab: (id: TabId) => void;
  children: React.ReactNode;
}) {
  const isActive = activeTab === id;
  return (
    <button
      onClick={() => setActiveTab(id)}
      className={`flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition
      ${isActive ? 'bg-slate-950 text-primary-100 shadow' : 'text-slate-400 hover:text-slate-100'}`}
    >
      {children}
    </button>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  tone = 'neutral',
}: {
  title: string;
  value: string;
  subtitle?: string;
  tone?: 'neutral' | 'positive' | 'negative';
}) {
  const valueColor =
    tone === 'positive'
      ? 'text-emerald-300'
      : tone === 'negative'
      ? 'text-rose-300'
      : 'text-slate-50';

  return (
    <div className="flex flex-col justify-between rounded-2xl bg-slate-900/80 p-4 shadow ring-1 ring-white/10">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
          {title}
        </p>
        <p className={`mt-2 text-xl font-semibold ${valueColor}`}>{value}</p>
      </div>
      {subtitle && <p className="mt-2 text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}

interface PriceHistoryPoint {
  time: string;
  [key: string]: string | number;
}

function MarketTab() {
  const [prices, setPrices] = useState<Record<string, any>>({});
  const [priceHistory, setPriceHistory] = useState<Record<string, PriceHistoryPoint[]>>({});
  const [loading, setLoading] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [showAllPairs, setShowAllPairs] = useState(false);
  const maxHistoryPoints = 50; // Keep last 50 data points

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const data = await marketApi.getPrices(showAllPairs);
        if (!cancelled) {
          setPrices(data || {});
          
          // Update price history
          const now = new Date().toISOString();
          setPriceHistory((prev) => {
            const updated = { ...prev };
            const symbols = Object.keys(data || {});
            
            symbols.forEach((symbol) => {
              const exchanges = (data as any)[symbol] as Record<string, any>;
              const exchangeNames = Object.keys(exchanges);
              
              if (!updated[symbol]) {
                updated[symbol] = [];
              }
              
              // Create new data point
              const newPoint: PriceHistoryPoint = { time: now };
              exchangeNames.forEach((ex) => {
                const exData = exchanges[ex];
                if (exData) {
                  if (typeof exData.bid === 'number') {
                    newPoint[`${ex}_bid`] = exData.bid;
                  }
                  if (typeof exData.ask === 'number') {
                    newPoint[`${ex}_ask`] = exData.ask;
                  }
                  if (typeof exData.mid === 'number') {
                    newPoint[`${ex}_mid`] = exData.mid;
                  }
                  if (typeof exData.spread === 'number') {
                    // Calculate spread percentage: (spread / mid) * 100
                    const mid = exData.mid || ((exData.bid + exData.ask) / 2);
                    if (mid > 0) {
                      newPoint[`${ex}_spread`] = (exData.spread / mid) * 100;
                    } else {
                      newPoint[`${ex}_spread`] = 0;
                    }
                  }
                }
              });
              
              // Add new point and limit history
              updated[symbol] = [...(updated[symbol] || []), newPoint].slice(-maxHistoryPoints);
            });
            
            return updated;
          });
          
          // Auto-select first symbol if none selected
          if (!selectedSymbol && Object.keys(data || {}).length > 0) {
            setSelectedSymbol(Object.keys(data || {})[0]);
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    
    load();
    
    // Auto-refresh every 2 seconds
    const interval = setInterval(() => {
      if (!cancelled) {
        load();
      }
    }, 2000);
    
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [showAllPairs]);

  if (loading && Object.keys(prices).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-8 text-sm text-slate-400">
        <span>Loading market data…</span>
      </div>
    );
  }

  const symbols = Object.keys(prices);

  if (!symbols.length) {
    return (
      <p className="text-sm text-slate-400">
        No market data available yet. Ensure the bot is running.
      </p>
    );
  }

  const currentSymbol = selectedSymbol || symbols[0];
  const exchanges = prices[currentSymbol] as Record<string, any>;
  const exchangeNames = Object.keys(exchanges || {});
  const history = priceHistory[currentSymbol] || [];

  // Prepare comparison data for bar chart
  const comparisonData = exchangeNames.map((ex) => {
    const data = exchanges[ex];
    return {
      exchange: ex,
      bid: data?.bid || 0,
      ask: data?.ask || 0,
      mid: data?.mid || 0,
    };
  });

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={showAllPairs}
              onChange={(e) => setShowAllPairs(e.target.checked)}
              className="h-4 w-4 rounded border-slate-600 bg-slate-900"
            />
            Show all available pairs ({symbols.length} pairs)
          </label>
        </div>
        <div className="text-xs text-slate-500">
          {showAllPairs 
            ? 'Showing all trading pairs from connected exchanges'
            : 'Showing only configured trading pairs'}
        </div>
      </div>
      
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

      {/* Charts Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Price Trends Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <PriceChart
            data={history}
            exchanges={exchangeNames}
            dataKey="mid"
            title={`Mid Price Trend: ${currentSymbol}`}
          />
        </div>

        {/* Price Comparison Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <PriceComparisonChart data={comparisonData} symbol={currentSymbol} />
        </div>

        {/* Bid/Ask Trends */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <PriceChart
            data={history}
            exchanges={exchangeNames}
            dataKey="bid"
            title={`Bid Price Trend: ${currentSymbol}`}
          />
        </div>

        {/* Spread Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <SpreadChart
            data={history}
            exchanges={exchangeNames}
            title={`Spread Trend: ${currentSymbol}`}
          />
        </div>
      </div>

      {/* Current Prices Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
        <h3 className="mb-4 text-sm font-semibold text-slate-100">
          Current Prices: {currentSymbol}
        </h3>
        <div className="space-y-2 text-xs">
          {Object.entries(exchanges || {}).map(([ex, data]) => {
            const bid =
              data && typeof data.bid === 'number'
                ? data.bid.toFixed(4)
                : '—';
            const ask =
              data && typeof data.ask === 'number'
                ? data.ask.toFixed(4)
                : '—';
            const mid =
              data && typeof data.mid === 'number'
                ? data.mid.toFixed(4)
                : '—';
            const spread =
              data && typeof data.spread === 'number'
                ? data.spread.toFixed(4)
                : '—';
            return (
              <div
                key={ex}
                className="flex items-center justify-between rounded-md bg-slate-900/80 px-3 py-2"
              >
                <span className="font-medium text-slate-200">{ex}</span>
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
      </div>
    </div>
  );
}

function OpportunitiesTab({ opportunities }: { opportunities: Opportunity[] }) {
  // Prepare chart data
  const profitTrendData = opportunities
    .slice()
    .reverse()
    .map((opp) => ({
      time: opp.timestamp,
      profit_percent: opp.profit_percent,
      symbol: opp.symbol,
    }))
    .slice(0, 100); // Last 100 opportunities

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
    .slice(0, 10); // Top 10 symbols

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
    .slice(0, 10); // Top 10 pairs

  if (!opportunities.length) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-slate-400">
          No arbitrage opportunities found yet. Let the bot run for a while.
        </p>
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-6">
          <h3 className="mb-2 text-sm font-semibold text-slate-200">
            What to expect:
          </h3>
          <ul className="list-inside list-disc space-y-1 text-xs text-slate-400">
            <li>Opportunities appear when price differences between exchanges exceed your profit threshold</li>
            <li>Charts will show profit trends, symbol distribution, and exchange pair analysis</li>
            <li>Make sure multiple exchanges are connected and the bot is actively monitoring prices</li>
          </ul>
        </div>
      </div>
    );
  }

  const totalOpportunities = opportunities.length;
  const avgProfit = opportunities.reduce((sum, opp) => sum + opp.profit_percent, 0) / totalOpportunities;
  const maxProfit = Math.max(...opportunities.map((opp) => opp.profit_percent));

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <div className="text-xs text-slate-400">Total Opportunities</div>
          <div className="mt-1 text-2xl font-bold text-slate-100">{totalOpportunities}</div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <div className="text-xs text-slate-400">Average Profit</div>
          <div className="mt-1 text-2xl font-bold text-emerald-400">
            {avgProfit.toFixed(2)}%
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <div className="text-xs text-slate-400">Max Profit</div>
          <div className="mt-1 text-2xl font-bold text-emerald-300">
            {maxProfit.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Profit Trend Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <OpportunityChart
            data={profitTrendData}
            title="Profit Trend Over Time"
          />
        </div>

        {/* Symbol Distribution Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <OpportunityDistributionChart
            data={distributionData}
            title="Opportunities by Symbol"
          />
        </div>

        {/* Exchange Pair Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 lg:col-span-2">
          <ExchangePairChart
            data={pairData}
            title="Top Exchange Pairs (Buy → Sell)"
          />
        </div>
      </div>

      {/* Opportunities Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
        <h3 className="mb-4 text-sm font-semibold text-slate-100">
          Recent Opportunities ({opportunities.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-800 text-sm">
            <thead className="bg-slate-900/80">
              <tr>
                <Th>Time</Th>
                <Th>Symbol</Th>
                <Th>Buy From</Th>
                <Th>Sell To</Th>
                <Th>Buy Price</Th>
                <Th>Sell Price</Th>
                <Th>Profit %</Th>
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
                  <tr
                    key={`${opp.symbol}-${opp.timestamp}-${idx}`}
                    className="hover:bg-slate-900/60"
                  >
                    <Td>{new Date(opp.timestamp).toLocaleTimeString()}</Td>
                    <Td className="font-semibold">{opp.symbol}</Td>
                    <Td>{opp.buy_exchange}</Td>
                    <Td>{opp.sell_exchange}</Td>
                    <Td>${opp.buy_price.toFixed(4)}</Td>
                    <Td>${opp.sell_price.toFixed(4)}</Td>
                    <Td className={profitClass}>
                      {opp.profit_percent < 0.1 
                        ? opp.profit_percent.toFixed(4) 
                        : opp.profit_percent.toFixed(2)}%
                    </Td>
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
      </div>
    </div>
  );
}

function TradesTab({ trades }: { trades: Trade[] }) {
  if (!trades.length) {
    return (
      <p className="text-sm text-slate-400">
        No trades executed yet. Opportunities that meet your thresholds will show here.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-800 text-sm">
        <thead className="bg-slate-900/80">
          <tr>
            <Th>Time</Th>
            <Th>Symbol</Th>
            <Th>Buy From</Th>
            <Th>Sell To</Th>
            <Th>Amount</Th>
            <Th>Profit (USD)</Th>
            <Th>Profit %</Th>
            <Th>Status</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {trades.map((t) => {
            const profitClass =
              t.profit_usd >= 0 ? 'text-emerald-300' : 'text-rose-300';
            return (
              <tr key={`${t.symbol}-${t.timestamp}`} className="hover:bg-slate-900/60">
                <Td>{new Date(t.timestamp).toLocaleTimeString()}</Td>
                <Td className="font-semibold">{t.symbol}</Td>
                <Td>{t.buy_exchange}</Td>
                <Td>{t.sell_exchange}</Td>
                <Td>{t.amount.toFixed(6)}</Td>
                <Td className={profitClass}>${t.profit_usd.toFixed(2)}</Td>
                <Td className={profitClass}>{t.profit_percent.toFixed(2)}%</Td>
                <Td>{t.status}</Td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function BalancesTab({ balances }: { balances: Record<string, Balance> }) {
  const assets = Object.keys(balances);

  if (!assets.length) {
    return (
      <p className="text-sm text-slate-400">
        No balance data yet. Ensure exchanges are configured and the bot is running.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-800 text-sm">
        <thead className="bg-slate-900/80">
          <tr>
            <Th>Asset</Th>
            <Th>Total Amount</Th>
            <Th>Value (USD)</Th>
            <Th>Exchange Distribution</Th>
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
                <Td className="font-semibold">{asset}</Td>
                <Td>{bal.total_amount.toFixed(6)}</Td>
                <Td>${bal.total_value_usd.toFixed(2)}</Td>
                <Td>{exchanges}</Td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ConfigTab({
  tradingConfig,
  setTradingConfig,
  riskConfig,
  setRiskConfig,
  onSaveTrading,
  onSaveRisk,
  savingTrading,
  savingRisk,
  exchangesConfig,
  onRefreshExchanges,
  ephemeralExchanges,
  setEphemeralExchanges,
}: {
  tradingConfig: TradingConfig | null;
  setTradingConfig: (c: TradingConfig | null) => void;
  riskConfig: RiskConfig | null;
  setRiskConfig: (c: RiskConfig | null) => void;
  onSaveTrading: () => void;
  onSaveRisk: () => void;
  savingTrading: boolean;
  savingRisk: boolean;
  exchangesConfig: ExchangesResponse | null;
  onRefreshExchanges: () => void;
  ephemeralExchanges: EphemeralExchange[];
  setEphemeralExchanges: (list: EphemeralExchange[]) => void;
}) {
  const [exchangeType, setExchangeType] = useState<'cex' | 'dex'>('cex');
  const [selectedCex, setSelectedCex] = useState<string>('binance');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [enableExchange, setEnableExchange] = useState(true);
  const [savingExchange, setSavingExchange] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);

  const configuredExchanges: ConfiguredExchange[] =
    exchangesConfig?.configured_exchanges || [];

  const handleSaveExchange = async () => {
    if (!selectedCex) {
      return;
    }
    
    // For CEX, require API key and secret
    if (exchangeType === 'cex') {
      if (!apiKey || !apiSecret) {
        return;
      }
      
      setSavingExchange(true);
      try {
        await configApi.saveExchange({
          exchange_name: selectedCex,
          api_key: apiKey,
          api_secret: apiSecret,
          passphrase: passphrase || undefined,
          testnet: false,
          enabled: enableExchange,
        });
        
        // Also add to ephemeral list for immediate use
        const existing = ephemeralExchanges.filter((e) => e.exchange_name !== selectedCex);
        const updated: EphemeralExchange = {
          exchange_name: selectedCex,
          api_key: apiKey,
          api_secret: apiSecret,
          passphrase: passphrase || null,
          testnet: false,
          enabled: enableExchange,
        };
        setEphemeralExchanges([...existing, updated]);
        
        // Clear form
        setApiKey('');
        setApiSecret('');
        setPassphrase('');
        
        // Refresh exchanges list
        await onRefreshExchanges();
      } catch (e: any) {
        alert(`Failed to save: ${e?.message || 'Unknown error'}`);
      } finally {
        setSavingExchange(false);
      }
      return;
    }
    
    // For DEX, require private key
    if (exchangeType === 'dex') {
      if (!apiKey) {
        alert('Please enter your wallet private key');
        return;
      }
      
      setSavingExchange(true);
      try {
        // Determine chain
        let chain: string | undefined;
        if (selectedCex === 'pancakeswap') chain = 'bsc';
        else if (selectedCex === 'uniswap_v2') chain = 'ethereum';
        else if (selectedCex === 'quickswap') chain = 'polygon';
        else if (selectedCex === 'galaswap') chain = 'gala';
        
        await configApi.saveDEX({
          exchange_name: selectedCex,
          private_key: apiKey,
          wallet_address: selectedCex === 'galaswap' ? passphrase : undefined,
          rpc_url: apiSecret || undefined,
          chain: chain,
          enabled: enableExchange,
        });
        
        // Clear form
        setApiKey('');
        setApiSecret('');
        setPassphrase('');
        
        // Refresh exchanges list
        await onRefreshExchanges();
      } catch (e: any) {
        alert(`Failed to save DEX config: ${e?.message || 'Unknown error'}`);
      } finally {
        setSavingExchange(false);
      }
      return;
    }
  };

  const handleToggleExchange = async (ex: ConfiguredExchange) => {
    try {
      setToggling(ex.name);
      await configApi.toggleExchange(ex.name, !ex.enabled);
      await onRefreshExchanges();
    } finally {
      setToggling(null);
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-3">
      {/* Exchange API keys */}
      <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4 md:col-span-1">
        <h3 className="text-sm font-semibold text-slate-100">Exchange Configuration</h3>
        <p className="text-xs text-slate-500">
          Configure CEX (API keys) or DEX (wallet keys, RPC URLs). All credentials are encrypted and stored securely in the database.
        </p>
        <label className="block text-xs font-medium text-slate-300">
          Exchange Type
          <select
            value={exchangeType}
            onChange={(e) => {
              setExchangeType(e.target.value as 'cex' | 'dex');
              setSelectedCex('');
            }}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-primary-500/40 focus:ring"
          >
            <option value="cex">Centralized Exchange (CEX)</option>
            <option value="dex">Decentralized Exchange (DEX)</option>
          </select>
        </label>
        <label className="block text-xs font-medium text-slate-300">
          Exchange
          <select
            value={selectedCex}
            onChange={(e) => setSelectedCex(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-primary-500/40 focus:ring"
          >
            <option value="">Select an exchange...</option>
            {exchangeType === 'cex' && exchangesConfig?.available_cex?.map((ex) => (
              <option key={ex.name} value={ex.name}>
                {ex.display_name}
              </option>
            ))}
            {exchangeType === 'dex' && exchangesConfig?.available_dex?.map((ex) => (
              <option key={ex.name} value={ex.name}>
                {ex.display_name} ({ex.chain})
              </option>
            ))}
          </select>
        </label>
        {exchangeType === 'cex' && (
          <>
            <label className="block text-xs font-medium text-slate-300">
              API Key
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-primary-500/40 focus:ring"
              />
            </label>
            <label className="block text-xs font-medium text-slate-300">
              API Secret
              <input
                type="password"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-primary-500/40 focus:ring"
              />
            </label>
          </>
        )}
        {selectedCex === 'okx' && exchangeType === 'cex' && (
          <label className="block text-xs font-medium text-slate-300">
            Passphrase (OKX)
            <input
              type="password"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-primary-500/40 focus:ring"
            />
          </label>
        )}
        {exchangeType === 'dex' && (
          <>
            <label className="block text-xs font-medium text-slate-300">
              Wallet Private Key
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="0x..."
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-primary-500/40 focus:ring"
              />
              <p className="mt-1 text-[10px] text-slate-500">
                Your wallet private key (starts with 0x). Keep this secure!
              </p>
            </label>
            {selectedCex === 'galaswap' && (
              <label className="block text-xs font-medium text-slate-300">
                Gala Wallet Address
                <input
                  type="text"
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  placeholder="0x..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-primary-500/40 focus:ring"
                />
                <p className="mt-1 text-[10px] text-slate-500">
                  Your Gala wallet address (public key)
                </p>
              </label>
            )}
            <label className="block text-xs font-medium text-slate-300">
              RPC URL (Optional - uses defaults if empty)
              <input
                type="text"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder="https://..."
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-primary-500/40 focus:ring"
              />
              <p className="mt-1 text-[10px] text-slate-500">
                Blockchain RPC endpoint. Leave empty to use default public RPCs.
              </p>
            </label>
            <details className="rounded-lg border border-slate-700 bg-slate-900/50 p-2 text-xs">
              <summary className="cursor-pointer font-medium text-slate-300">
                Advanced: Router & Factory Addresses (Optional)
              </summary>
              <div className="mt-2 space-y-2">
                <label className="block text-xs font-medium text-slate-300">
                  Router Address
                  <input
                    type="text"
                    placeholder="0x..."
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 outline-none"
                  />
                </label>
                <label className="block text-xs font-medium text-slate-300">
                  Factory Address
                  <input
                    type="text"
                    placeholder="0x..."
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-100 outline-none"
                  />
                </label>
                <p className="text-[10px] text-slate-500">
                  Default addresses are used if not specified. Only change if you know what you're doing.
                </p>
              </div>
            </details>
          </>
        )}
        <label className="mt-1 flex items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={enableExchange}
            onChange={(e) => setEnableExchange(e.target.checked)}
            className="h-3 w-3 rounded border-slate-600 bg-slate-900"
          />
          Enable this exchange
        </label>
        <button
          onClick={handleSaveExchange}
          disabled={savingExchange}
          className="mt-2 inline-flex w-full items-center justify-center rounded-lg bg-primary-500 px-3 py-2 text-sm font-semibold text-slate-950 shadow hover:bg-primary-400 disabled:cursor-not-allowed disabled:bg-slate-700"
        >
          {savingExchange ? 'Saving…' : 'Save Exchange Config'}
        </button>
      </div>

      {/* Trading config */}
      <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4 md:col-span-1">
        <h3 className="text-sm font-semibold text-slate-100">Trading Parameters</h3>
        {tradingConfig ? (
          <>
            <NumberField
              label="Min Profit Threshold (%)"
              value={tradingConfig.min_profit_threshold}
              onChange={(v) =>
                setTradingConfig({ ...tradingConfig, min_profit_threshold: v })
              }
            />
            <NumberField
              label="Max Trade Size (%)"
              value={tradingConfig.max_trade_size_percent}
              onChange={(v) =>
                setTradingConfig({ ...tradingConfig, max_trade_size_percent: v })
              }
            />
            <NumberField
              label="Max Slippage (%)"
              value={tradingConfig.max_slippage_percent}
              onChange={(v) =>
                setTradingConfig({ ...tradingConfig, max_slippage_percent: v })
              }
            />
            <button
              onClick={onSaveTrading}
              disabled={savingTrading}
              className="mt-1 inline-flex w-full items-center justify-center rounded-lg bg-primary-500 px-3 py-2 text-sm font-semibold text-slate-950 shadow hover:bg-primary-400 disabled:cursor-not-allowed disabled:bg-slate-700"
            >
              {savingTrading ? 'Saving…' : 'Save Trading Config'}
            </button>
          </>
        ) : (
          <p className="text-sm text-slate-400">
            Unable to load trading config. Check backend connection.
          </p>
        )}
      </div>

      {/* Risk config + exchange list */}
      <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4 md:col-span-1">
        <h3 className="text-sm font-semibold text-slate-100">Risk Management</h3>
        {riskConfig ? (
          <>
            <NumberField
              label="Max Drawdown (%)"
              value={riskConfig.max_drawdown_percent}
              onChange={(v) =>
                setRiskConfig({ ...riskConfig, max_drawdown_percent: v })
              }
            />
            <NumberField
              label="Max Daily Loss (%)"
              value={riskConfig.max_daily_loss_percent}
              onChange={(v) =>
                setRiskConfig({ ...riskConfig, max_daily_loss_percent: v })
              }
            />
            <NumberField
              label="Max Position Size (USD)"
              value={riskConfig.max_position_size_usd}
              onChange={(v) =>
                setRiskConfig({ ...riskConfig, max_position_size_usd: v })
              }
            />
            <button
              onClick={onSaveRisk}
              disabled={savingRisk}
              className="mt-1 inline-flex w-full items-center justify-center rounded-lg bg-primary-500 px-3 py-2 text-sm font-semibold text-slate-950 shadow hover:bg-primary-400 disabled:cursor-not-allowed disabled:bg-slate-700"
            >
              {savingRisk ? 'Saving…' : 'Save Risk Config'}
            </button>
            <p className="mt-1 text-xs text-slate-500">
              Emergency stop and other safeguards are managed by the backend risk manager.
            </p>
          </>
        ) : (
          <p className="text-sm text-slate-400">
            Unable to load risk config. Check backend connection.
          </p>
        )}
      </div>

      {/* Configured exchanges list */}
      <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4 md:col-span-3">
        <h3 className="text-sm font-semibold text-slate-100">Configured Exchanges</h3>
        {configuredExchanges.length === 0 && ephemeralExchanges.length === 0 ? (
          <p className="text-sm text-slate-400">
            No exchanges configured for this session yet. Add API keys above, then start the bot.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-800 text-xs">
              <thead className="bg-slate-900/80">
                <tr>
                  <Th>Exchange</Th>
                  <Th>Type</Th>
                  <Th>Status</Th>
                  <Th>Testnet</Th>
                  <Th>Last Updated</Th>
                  <Th>Actions</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {configuredExchanges.map((ex) => {
                  const statusColor = ex.configured && ex.enabled
                    ? 'text-emerald-300'
                    : ex.configured
                    ? 'text-amber-300'
                    : 'text-rose-300';
                  const statusText = ex.configured && ex.enabled
                    ? 'Enabled'
                    : ex.configured
                    ? 'Disabled'
                    : 'No Keys';
                  return (
                    <tr key={ex.name} className="hover:bg-slate-900/60">
                      <Td className="font-semibold">{ex.name}</Td>
                      <Td>{ex.type.toUpperCase()}</Td>
                      <Td className={statusColor}>{statusText}</Td>
                      <Td>{ex.testnet ? 'Yes' : 'No'}</Td>
                      <Td>
                        {ex.last_updated
                          ? new Date(ex.last_updated).toLocaleString()
                          : '—'}
                      </Td>
                      <Td>
                        <button
                          onClick={() => handleToggleExchange(ex)}
                          disabled={toggling === ex.name || !ex.configured}
                          className="inline-flex items-center rounded-md bg-slate-800 px-2 py-1 text-[11px] font-medium text-slate-100 hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-900"
                        >
                          {toggling === ex.name
                            ? 'Updating…'
                            : ex.enabled
                            ? 'Disable'
                            : 'Enable'}
                        </button>
                      </Td>
                    </tr>
                  );
                })}
                {ephemeralExchanges.map((ex) => (
                  <tr key={`ephemeral-${ex.exchange_name}`} className="hover:bg-slate-900/60">
                    <Td className="font-semibold">{ex.exchange_name}</Td>
                    <Td>CEK (session)</Td>
                    <Td className="text-emerald-300">In-memory</Td>
                    <Td>{ex.testnet ? 'Yes' : 'No'}</Td>
                    <Td>—</Td>
                    <Td className="text-xs text-slate-500">Sent only when starting bot</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block text-xs font-medium text-slate-300">
      {label}
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 shadow-inner outline-none ring-primary-500/40 focus:ring"
      />
    </label>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
      {children}
    </th>
  );
}

function Td({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <td className={`px-3 py-2 align-middle text-xs text-slate-100 ${className}`}>
      {children}
    </td>
  );
}


