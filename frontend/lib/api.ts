/**
 * API client for arbitrage bot backend
 */

import axios from 'axios';

// Use relative URLs so requests go through Next.js server proxy
// The Next.js server (running in Docker) can access http://dashboard:8000
// The browser (client-side) uses relative URLs that get proxied
// Note: API calls already include '/api' prefix, so baseURL should be '/' or empty
const API_BASE = typeof window !== 'undefined' 
  ? '/'  // Client-side: use relative URL (proxied by Next.js)
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');  // Server-side: use full URL

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  // Basic auth will be handled per-request
  auth: {
    username: 'admin',
    password: 'admin', // TODO: Make this configurable
  },
  // Increase timeout for long-running requests
  timeout: 30000, // 30 seconds
  // Retry configuration
  validateStatus: function (status) {
    return status < 500; // Don't throw for 4xx errors, only 5xx
  },
});

// Types
export interface BotStatus {
  is_running: boolean;
  uptime_seconds: number;
  paper_trading: boolean;
  exchanges_connected: number;
  price_monitor_stats?: any;
  trade_stats?: any;
  risk_stats?: any;
  portfolio_stats?: any;
}

export interface Opportunity {
  symbol: string;
  buy_exchange: string;
  sell_exchange: string;
  buy_price: number;
  sell_price: number;
  profit_percent: number;
  profit_usd?: number;
  timestamp: string;
}

export interface Trade {
  symbol: string;
  buy_exchange: string;
  sell_exchange: string;
  amount: number;
  profit_usd: number;
  profit_percent: number;
  status: string;
  timestamp: string;
}

export interface Balance {
  total_amount: number;
  total_value_usd: number;
  exchanges: Record<string, number>;
}

export interface RiskMetrics {
  portfolio_value_usd: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  drawdown_percent: number;
  risk_level: string;
  trading_enabled: boolean;
  emergency_stop: boolean;
}

export interface TradeStatistics {
  total_trades: number;
  successful_trades: number;
  failed_trades: number;
  success_rate: number;
  total_profit_usd: number;
  average_profit_percent: number;
}

export interface TradingConfig {
  min_profit_threshold: number;
  max_trade_size_percent: number;
  max_slippage_percent: number;
  order_timeout_seconds: number;
  paper_trading: boolean;
}

export interface RiskConfig {
  max_drawdown_percent: number;
  max_daily_loss_percent: number;
  max_position_size_usd: number;
  emergency_stop_enabled: boolean;
}

export interface ConfiguredExchange {
  name: string;
  type: string;
  enabled: boolean;
  testnet: boolean;
  configured: boolean;
  last_updated: string | null;
}

export interface EphemeralExchange {
  exchange_name: string;
  api_key: string;
  api_secret: string;
  passphrase: string | null;
  testnet: boolean;
  enabled: boolean;
}

export interface ExchangesResponse {
  available_cex: any[];
  available_dex: any[];
  configured_exchanges: ConfiguredExchange[];
}

export interface BacktestResult {
  total_trades: number;
  successful_trades?: number;
  winning_trades: number;
  losing_trades: number;
  total_profit_usd?: number;
  total_profit_percent?: number;
  total_return: number; // Total return percentage
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  start_date?: string;
  end_date?: string;
  initial_capital: number;
  final_capital: number;
  message?: string;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  issues?: string[];
  bot: {
    running: boolean;
    uptime_seconds: number;
    paper_trading: boolean;
  };
  databases: {
    postgres: boolean;
    influxdb: boolean;
    redis?: boolean;
  };
  exchanges: {
    connected: number;
    total: number;
  };
  components: {
    price_monitor: boolean;
    trade_executor: boolean;
    risk_manager: boolean;
    portfolio_manager: boolean;
  };
}

export interface Allocation {
  current: Record<string, number>;
  target: Record<string, number>;
  rebalance_needed: boolean;
  total_value_usd: number;
  threshold?: number;
}

export interface TradingPair {
  symbol: string;
  min_trade_amount: number;
  enabled: boolean;
}

// API modules
export const botApi = {
  getStatus: async (): Promise<BotStatus> => {
    const res = await api.get('/api/bot/status');
    return res.data;
  },
  start: async (payload?: { exchanges?: EphemeralExchange[] }): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/bot/start', payload);
    return res.data;
  },
  stop: async (): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/bot/stop');
    return res.data;
  },
  emergencyStop: async (): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/bot/emergency-stop');
    return res.data;
  },
  setTradingMode: async (paperTrading: boolean): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/bot/trading/mode', { paper_trading: paperTrading });
    return res.data;
  },
};

export const marketApi = {
  getPrices: async (showAllPairs?: boolean): Promise<Record<string, any>> => {
    const params = showAllPairs ? { all_pairs: true } : {};
    const res = await api.get('/api/market/prices', { params });
    return res.data;
  },
  getOpportunities: async (): Promise<{ opportunities: Opportunity[] }> => {
    const res = await api.get('/api/market/opportunities');
    return res.data;
  },
  getSpreads: async (): Promise<{ spreads: Record<string, any> }> => {
    const res = await api.get('/api/market/spreads');
    return res.data;
  },
};

export const tradesApi = {
  getHistory: async (limit: number = 50): Promise<{ trades: Trade[] }> => {
    const res = await api.get(`/api/trades/history?limit=${limit}`);
    return res.data;
  },
  getStatistics: async (): Promise<TradeStatistics> => {
    const res = await api.get('/api/trades/statistics');
    return res.data;
  },
};

export const portfolioApi = {
  getSummary: async (): Promise<any> => {
    const res = await api.get('/api/portfolio/summary');
    return res.data;
  },
  getBalances: async (): Promise<{ balances: Record<string, Balance> }> => {
    const res = await api.get('/api/portfolio/balances');
    return res.data;
  },
};

export const riskApi = {
  getMetrics: async (): Promise<RiskMetrics> => {
    const res = await api.get('/api/risk/metrics');
    return res.data;
  },
  saveRiskConfig: async (config: RiskConfig): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/risk/config', config);
    return res.data;
  },
};

export const configApi = {
  getTradingConfig: async (): Promise<TradingConfig> => {
    const res = await api.get('/api/config/trading');
    return res.data;
  },
  saveTradingConfig: async (config: TradingConfig): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/config/trading', config);
    return res.data;
  },
  getRiskConfig: async (): Promise<RiskConfig> => {
    const res = await api.get('/api/config/risk');
    return res.data;
  },
  saveRiskConfig: async (config: RiskConfig): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/config/risk', config);
    return res.data;
  },
  getExchanges: async (): Promise<ExchangesResponse> => {
    const res = await api.get('/api/config/exchanges');
    return res.data;
  },
  saveExchange: async (config: {
    exchange_name: string;
    api_key: string;
    api_secret: string;
    passphrase?: string;
    testnet?: boolean;
    enabled?: boolean;
  }): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/config/exchange', config);
    return res.data;
  },
  saveDEX: async (config: {
    exchange_name: string;
    private_key: string;
    wallet_address?: string;
    rpc_url?: string;
    chain?: string;
    enabled?: boolean;
  }): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/config/dex', config);
    return res.data;
  },
  toggleExchange: async (exchangeName: string, enabled: boolean): Promise<void> => {
    // This would need to be implemented in the backend
    // For now, we'll just refresh the exchanges list
    await configApi.getExchanges();
  },
};

export const backtestApi = {
  runBacktest: async (
    startDate: string,
    endDate: string,
    initialCapital: number,
    minProfitThreshold?: number
  ): Promise<BacktestResult> => {
    const res = await api.post('/api/backtest/run', {
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      min_profit_threshold: minProfitThreshold,
    });
    return res.data;
  },
};

export const systemApi = {
  getHealth: async (): Promise<SystemHealth> => {
    const res = await api.get('/health');
    return res.data;
  },
  getLogs: async (level?: string, limit: number = 100): Promise<string[]> => {
    const params = level ? { level, limit } : { limit };
    const res = await api.get('/api/system/logs', { params });
    return res.data.logs || [];
  },
};

export const rebalanceApi = {
  getAllocation: async (): Promise<Allocation> => {
    const res = await api.get('/api/portfolio/summary');
    return {
      current: res.data.allocation || {},
      target: res.data.target_allocation || {},
      rebalance_needed: res.data.rebalance_needed || false,
      total_value_usd: res.data.total_value_usd || 0,
    };
  },
  triggerRebalance: async (targetAllocation?: Record<string, number>): Promise<{ status: string; message: string; rebalanced?: boolean }> => {
    const res = await api.post('/api/portfolio/rebalance', { target_allocation: targetAllocation });
    return res.data;
  },
  updateAllocation: async (targetAllocation: Record<string, number>): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/portfolio/allocation', { target_allocation: targetAllocation });
    return res.data;
  },
};

export const tokensApi = {
  getPairs: async (): Promise<TradingPair[]> => {
    const res = await api.get('/api/config/trading-pairs');
    return res.data.pairs || [];
  },
  addPair: async (symbol: string, min_trade_amount: number, enabled: boolean = true): Promise<{ status: string; message: string }> => {
    const res = await api.post('/api/config/trading-pairs', {
      symbol,
      min_trade_amount,
      enabled,
    });
    return res.data;
  },
  updatePair: async (symbol: string, min_trade_amount: number, enabled: boolean): Promise<{ status: string; message: string }> => {
    const res = await api.put(`/api/config/trading-pairs/${symbol}`, {
      min_trade_amount,
      enabled,
    });
    return res.data;
  },
  deletePair: async (symbol: string): Promise<{ status: string; message: string }> => {
    const res = await api.delete(`/api/config/trading-pairs/${symbol}`);
    return res.data;
  },
};

