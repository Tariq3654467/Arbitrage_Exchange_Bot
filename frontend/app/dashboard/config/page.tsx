'use client';

import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { configApi, botApi, TradingConfig, RiskConfig, ExchangesResponse, ConfiguredExchange } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';

interface Notification {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

export default function ConfigPage() {
  const [tradingConfig, setTradingConfig] = useState<TradingConfig | null>(null);
  const [riskConfig, setRiskConfig] = useState<RiskConfig | null>(null);
  const [exchangesConfig, setExchangesConfig] = useState<ExchangesResponse | null>(null);
  const [savingTrading, setSavingTrading] = useState(false);
  const [savingRisk, setSavingRisk] = useState(false);
  const [savingExchange, setSavingExchange] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  
  // Exchange configuration form state
  const [exchangeType, setExchangeType] = useState<'cex' | 'dex'>('cex');
  const [selectedCex, setSelectedCex] = useState<string>('');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [walletAddress, setWalletAddress] = useState('');
  const [rpcUrl, setRpcUrl] = useState('');
  const [enableExchange, setEnableExchange] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);

  // Notification helper
  const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now().toString();
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  useEffect(() => {
    const loadConfig = async () => {
      try {
        setIsLoading(true);
        const [tConfig, rConfig, exch] = await Promise.allSettled([
          configApi.getTradingConfig(),
          configApi.getRiskConfig(),
          configApi.getExchanges()
        ]);

        if (tConfig.status === 'fulfilled') setTradingConfig(tConfig.value);
        if (rConfig.status === 'fulfilled') setRiskConfig(rConfig.value);
        if (exch.status === 'fulfilled') setExchangesConfig(exch.value);
      } catch (err) {
        console.error('Error loading config:', err);
        showNotification('Failed to load configuration', 'error');
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
    const interval = setInterval(loadConfig, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);
  
  const refreshExchanges = async () => {
    try {
      const data = await configApi.getExchanges();
      setExchangesConfig(data);
    } catch (err) {
      console.error('Error refreshing exchanges:', err);
      showNotification('Failed to refresh exchanges', 'error');
    }
  };
  
  const handleSaveExchange = async () => {
    if (!selectedCex) {
      showNotification('Please select an exchange', 'error');
      return;
    }
    
    if (exchangeType === 'cex') {
      if (!apiKey || !apiSecret) {
        showNotification('Please enter API key and secret', 'error');
        return;
      }
      
      setSavingExchange(true);
      try {
        await configApi.saveExchange({
          exchange_name: selectedCex,
          api_key: apiKey,
          api_secret: apiSecret,
          passphrase: undefined,
          testnet: false,
          enabled: enableExchange,
        });
        
        // Clear form
        setApiKey('');
        setApiSecret('');
        setWalletAddress('');
        setRpcUrl('');
        setSelectedCex('');
        
        // Refresh exchanges list
        await refreshExchanges();
        showNotification('Exchange configured successfully!', 'success');
      } catch (err: any) {
        showNotification(err?.response?.data?.detail || err?.message || 'Failed to save exchange', 'error');
      } finally {
        setSavingExchange(false);
      }
    } else {
      // DEX configuration
      if (!apiKey) {
        showNotification('Please enter your wallet private key', 'error');
        return;
      }
      
      if (selectedCex === 'galaswap' && !walletAddress) {
        showNotification('Gala wallet address is required for Galaswap', 'error');
        return;
      }
      
      setSavingExchange(true);
      try {
        await configApi.saveDEX({
          exchange_name: selectedCex,
          private_key: apiKey,
          wallet_address: selectedCex === 'galaswap' ? walletAddress : undefined,
          rpc_url: rpcUrl || undefined,
          chain: selectedCex === 'galaswap' ? 'gala' : undefined,
          enabled: enableExchange,
        });
        
        // Clear form
        setApiKey('');
        setApiSecret('');
        setWalletAddress('');
        setRpcUrl('');
        setSelectedCex('');
        
        // Refresh exchanges list
        await refreshExchanges();
        showNotification('DEX configured successfully!', 'success');
      } catch (err: any) {
        showNotification(err?.response?.data?.detail || err?.message || 'Failed to save DEX config', 'error');
      } finally {
        setSavingExchange(false);
      }
    }
  };
  
  const handleToggleExchange = async (ex: ConfiguredExchange) => {
    try {
      setToggling(ex.name);
      await configApi.toggleExchange(ex.name, !ex.enabled);
      await refreshExchanges();
      showNotification(`${ex.name} ${!ex.enabled ? 'enabled' : 'disabled'}`, 'success');
    } catch (err: any) {
      showNotification(err?.response?.data?.detail || err?.message || 'Failed to toggle exchange', 'error');
    } finally {
      setToggling(null);
    }
  };

  const handleSaveTrading = async () => {
    if (!tradingConfig) return;
    try {
      setSavingTrading(true);
      await configApi.saveTradingConfig(tradingConfig);
      showNotification('Trading config saved successfully', 'success');
    } catch (err: any) {
      showNotification(err?.response?.data?.detail || err?.message || 'Failed to save trading config', 'error');
    } finally {
      setSavingTrading(false);
    }
  };

  const handleSaveRisk = async () => {
    if (!riskConfig) return;
    try {
      setSavingRisk(true);
      await configApi.saveRiskConfig(riskConfig);
      showNotification('Risk config saved successfully', 'success');
    } catch (err: any) {
      showNotification(err?.response?.data?.detail || err?.message || 'Failed to save risk config', 'error');
    } finally {
      setSavingRisk(false);
    }
  };

  const NumberField = ({ label, value, onChange, min, max, step }: { 
    label: string; 
    value: number; 
    onChange: (v: number) => void;
    min?: number;
    max?: number;
    step?: number;
  }) => (
    <label className="block text-sm font-medium text-slate-300">
      {label}
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step || 0.01}
        onChange={(e) => {
          const val = parseFloat(e.target.value) || 0;
          onChange(val);
        }}
        className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-blue-500/40 focus:ring-2 transition-all"
      />
    </label>
  );

  return (
    <DashboardLayout>
      {/* Notification Toast Container */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {notifications.map((notif) => (
          <div
            key={notif.id}
            className={`min-w-[300px] rounded-lg px-4 py-3 shadow-lg backdrop-blur-sm animate-in slide-in-from-right ${
              notif.type === 'success'
                ? 'bg-emerald-600/90 text-white'
                : notif.type === 'error'
                ? 'bg-red-600/90 text-white'
                : 'bg-blue-600/90 text-white'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{notif.message}</span>
              <button
                onClick={() => setNotifications(prev => prev.filter(n => n.id !== notif.id))}
                className="ml-4 text-white/80 hover:text-white"
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-6">
        {/* Exchange API Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Exchange Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-400">
              Configure your exchange API keys (CEX) or wallet credentials (DEX). All credentials are encrypted and stored securely.
            </p>
            
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block text-sm font-medium text-slate-300">
                Exchange Type
                <select
                  value={exchangeType}
                  onChange={(e) => {
                    setExchangeType(e.target.value as 'cex' | 'dex');
                    setSelectedCex('');
                    setApiKey('');
                    setApiSecret('');
                    setWalletAddress('');
                    setRpcUrl('');
                  }}
                  className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-blue-500/40 focus:ring-2 transition-all"
                >
                  <option value="cex">Centralized Exchange (CEX)</option>
                  <option value="dex">Decentralized Exchange (DEX)</option>
                </select>
              </label>
              
              <label className="block text-sm font-medium text-slate-300">
                Exchange
                <select
                  value={selectedCex}
                  onChange={(e) => setSelectedCex(e.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-blue-500/40 focus:ring-2 transition-all"
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
            </div>
            
            {exchangeType === 'cex' && selectedCex && (
              <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/50 p-4">
                <label className="block text-sm font-medium text-slate-300">
                  API Key
                  <input
                    type="text"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Enter your API key"
                    className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-blue-500/40 focus:ring-2 transition-all"
                  />
                </label>
                <label className="block text-sm font-medium text-slate-300">
                  API Secret
                  <input
                    type="password"
                    value={apiSecret}
                    onChange={(e) => setApiSecret(e.target.value)}
                    placeholder="Enter your API secret"
                    className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-blue-500/40 focus:ring-2 transition-all"
                  />
                </label>
              </div>
            )}
            
            {exchangeType === 'dex' && selectedCex && (
              <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/50 p-4">
                <label className="block text-sm font-medium text-slate-300">
                  Wallet Private Key
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="0x..."
                    className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-blue-500/40 focus:ring-2 transition-all font-mono"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Your wallet private key. Keep this secure!
                  </p>
                </label>
                {selectedCex === 'galaswap' && (
                  <label className="block text-sm font-medium text-slate-300">
                    Gala Wallet Address
                    <input
                      type="text"
                      value={walletAddress}
                      onChange={(e) => setWalletAddress(e.target.value)}
                      placeholder="0x..."
                      className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-blue-500/40 focus:ring-2 transition-all font-mono"
                    />
                  </label>
                )}
                <label className="block text-sm font-medium text-slate-300">
                  RPC URL (Optional)
                  <input
                    type="text"
                    value={rpcUrl}
                    onChange={(e) => setRpcUrl(e.target.value)}
                    placeholder="https://..."
                    className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-blue-500/40 focus:ring-2 transition-all"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Leave empty to use default public RPC endpoints
                  </p>
                </label>
              </div>
            )}
            
            {selectedCex && (
              <>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={enableExchange}
                    onChange={(e) => setEnableExchange(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-600 bg-slate-900 accent-blue-600"
                  />
                  Enable this exchange immediately
                </label>
                
                <Button
                  onClick={handleSaveExchange}
                  disabled={savingExchange || !selectedCex}
                  isLoading={savingExchange}
                  className="w-full"
                >
                  Save Exchange Configuration
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        {/* Paper Trading Toggle */}
        <Card className="border-2 border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-red-500/10">
          <CardHeader>
            <CardTitle>Trading Mode</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton variant="rectangular" height={120} />
            ) : tradingConfig ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-lg bg-slate-900/50 p-4">
                  <div>
                    <div className="text-lg font-semibold text-slate-200">
                      {tradingConfig.paper_trading ? 'Paper Trading Mode' : 'Live Trading Mode'}
                    </div>
                    <div className="mt-1 text-sm text-slate-400">
                      {tradingConfig.paper_trading 
                        ? 'All trades are simulated - no real money is used' 
                        : '⚠️ REAL TRADES - Real money at risk! All trades execute with actual funds.'}
                    </div>
                  </div>
                  <Badge variant={tradingConfig.paper_trading ? 'warning' : 'error'} size="lg">
                    {tradingConfig.paper_trading ? 'PAPER' : 'LIVE'}
                  </Badge>
                </div>
                <Button
                  onClick={async () => {
                    const newMode = !tradingConfig.paper_trading;
                    const confirmMsg = newMode
                      ? 'Switch to Paper Trading mode? (Simulated trades)'
                      : '🚨 Switch to LIVE TRADING mode? This will use REAL MONEY!';
                    if (!window.confirm(confirmMsg)) return;

                    try {
                      await botApi.setTradingMode(newMode);
                      const updated = await configApi.getTradingConfig();
                      setTradingConfig(updated);
                      showNotification(
                        `Switched to ${newMode ? 'Paper' : 'Live'} Trading mode. Bot restart required.`,
                        'info'
                      );
                    } catch (err: any) {
                      showNotification(
                        err?.response?.data?.detail || err?.message || 'Failed to change trading mode',
                        'error'
                      );
                    }
                  }}
                  variant={tradingConfig.paper_trading ? 'danger' : 'success'}
                  className="w-full"
                >
                  {tradingConfig.paper_trading ? '🚨 Switch to Live Trading' : 'Switch to Paper Trading'}
                </Button>
                <p className="text-xs text-slate-500 text-center">
                  Note: Changing trading mode requires bot restart to take effect
                </p>
              </div>
            ) : (
              <div className="text-sm text-slate-400">Unable to load trading config</div>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Trading Config */}
          <Card>
            <CardHeader>
              <CardTitle>Trading Parameters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoading ? (
                <Skeleton variant="rectangular" height={200} />
              ) : tradingConfig ? (
                <>
                  <NumberField
                    label="Min Profit Threshold (%)"
                    value={tradingConfig.min_profit_threshold}
                    onChange={(v) => setTradingConfig({ ...tradingConfig, min_profit_threshold: v })}
                    min={0}
                    step={0.001}
                  />
                  <NumberField
                    label="Max Trade Size (%)"
                    value={tradingConfig.max_trade_size_percent}
                    onChange={(v) => setTradingConfig({ ...tradingConfig, max_trade_size_percent: v })}
                    min={0}
                    max={100}
                  />
                  <NumberField
                    label="Max Slippage (%)"
                    value={tradingConfig.max_slippage_percent}
                    onChange={(v) => setTradingConfig({ ...tradingConfig, max_slippage_percent: v })}
                    min={0}
                    max={10}
                  />
                  <Button
                    onClick={handleSaveTrading}
                    disabled={savingTrading}
                    isLoading={savingTrading}
                    className="w-full"
                  >
                    Save Trading Config
                  </Button>
                </>
              ) : (
                <p className="text-sm text-slate-400">Unable to load trading config</p>
              )}
            </CardContent>
          </Card>

          {/* Risk Config */}
          <Card>
            <CardHeader>
              <CardTitle>Risk Management</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoading ? (
                <Skeleton variant="rectangular" height={200} />
              ) : riskConfig ? (
                <>
                  <NumberField
                    label="Max Drawdown (%)"
                    value={riskConfig.max_drawdown_percent}
                    onChange={(v) => setRiskConfig({ ...riskConfig, max_drawdown_percent: v })}
                    min={0}
                    max={100}
                  />
                  <NumberField
                    label="Max Daily Loss (%)"
                    value={riskConfig.max_daily_loss_percent}
                    onChange={(v) => setRiskConfig({ ...riskConfig, max_daily_loss_percent: v })}
                    min={0}
                    max={100}
                  />
                  <NumberField
                    label="Max Position Size (USD)"
                    value={riskConfig.max_position_size_usd}
                    onChange={(v) => setRiskConfig({ ...riskConfig, max_position_size_usd: v })}
                    min={0}
                    step={100}
                  />
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                    <label className="text-sm font-medium text-slate-300">
                      Emergency Stop
                    </label>
                    <input
                      type="checkbox"
                      checked={riskConfig.emergency_stop_enabled}
                      onChange={(e) => setRiskConfig({ ...riskConfig, emergency_stop_enabled: e.target.checked })}
                      className="h-4 w-4 rounded border-slate-600 bg-slate-900 accent-red-600"
                    />
                  </div>
                  <p className="text-xs text-slate-500">
                    Emergency stop will immediately halt all trading when triggered
                  </p>
                  <Button
                    onClick={handleSaveRisk}
                    disabled={savingRisk}
                    isLoading={savingRisk}
                    className="w-full"
                  >
                    Save Risk Config
                  </Button>
                </>
              ) : (
                <p className="text-sm text-slate-400">Unable to load risk config</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Configured Exchanges */}
        <Card>
          <CardHeader>
            <CardTitle>Configured Exchanges</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton variant="rectangular" height={200} />
            ) : !exchangesConfig?.configured_exchanges?.length ? (
              <div className="py-12 text-center">
                <p className="text-slate-400">No exchanges configured yet.</p>
                <p className="mt-2 text-sm text-slate-500">Add API keys using the form above.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-800">
                  <thead className="bg-slate-900/80">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-400">Exchange</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-400">Type</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-400">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-400">Last Updated</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {exchangesConfig.configured_exchanges.map((ex) => {
                      const statusColor = ex.configured && ex.enabled
                        ? 'text-emerald-400'
                        : ex.configured
                        ? 'text-amber-400'
                        : 'text-red-400';
                      const statusText = ex.configured && ex.enabled
                        ? 'Active'
                        : ex.configured
                        ? 'Disabled'
                        : 'No Keys';
                      return (
                        <tr key={ex.name} className="hover:bg-slate-900/60 transition-colors">
                          <td className="px-4 py-3 font-semibold text-slate-200 capitalize">{ex.name}</td>
                          <td className="px-4 py-3 text-slate-300 uppercase text-xs">{ex.type}</td>
                          <td className={`px-4 py-3 font-medium ${statusColor}`}>{statusText}</td>
                          <td className="px-4 py-3 text-sm text-slate-400" suppressHydrationWarning>
                            {ex.last_updated
                              ? new Date(ex.last_updated).toLocaleString()
                              : '—'}
                          </td>
                          <td className="px-4 py-3">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleToggleExchange(ex)}
                              disabled={toggling === ex.name || !ex.configured}
                              isLoading={toggling === ex.name}
                            >
                              {ex.enabled ? 'Disable' : 'Enable'}
                            </Button>
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
