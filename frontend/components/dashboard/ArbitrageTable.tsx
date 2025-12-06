'use client';

import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface Opportunity {
  symbol: string;
  buy_exchange: string;
  sell_exchange: string;
  buy_price: number;
  sell_price: number;
  spread: number;
  profit_percent: number;
  net_profit: number;
  timestamp: string;
}

interface ArbitrageTableProps {
  opportunities: Opportunity[];
  isLoading?: boolean;
}

export function ArbitrageTable({ opportunities, isLoading }: ArbitrageTableProps) {
  if (isLoading) {
    return (
      <div className="card-premium rounded-card p-6">
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-[#1e293b] rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (opportunities.length === 0) {
    return (
      <div className="card-premium rounded-card p-12 text-center">
        <p className="text-gray-400">No arbitrage opportunities detected</p>
        <p className="text-sm text-gray-500 mt-2">Waiting for market conditions...</p>
      </div>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 6
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <div className="card-premium rounded-card overflow-hidden">
      <div className="px-6 py-4 border-b border-[#1e293b]">
        <h3 className="text-lg font-semibold text-white">Live Arbitrage Opportunities</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-[#1e293b]/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Pair</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Route</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Buy Price</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Sell Price</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Spread</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Net Profit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e293b]">
            {opportunities.map((opp, idx) => (
              <tr
                key={`${opp.symbol}-${idx}`}
                className="table-row-hover bg-transparent hover:bg-[#1e293b]/30"
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-semibold text-white">{opp.symbol}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-[#4ade80]">{opp.buy_exchange}</span>
                    <ArrowUpRight className="h-4 w-4 text-gray-500" />
                    <span className="text-[#60a5fa]">{opp.sell_exchange}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <div className="text-sm font-mono text-gray-300">{formatCurrency(opp.buy_price)}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <div className="text-sm font-mono text-gray-300">{formatCurrency(opp.sell_price)}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <div className={`text-sm font-semibold font-mono ${
                    opp.spread > 0 ? 'text-[#4ade80]' : 'text-gray-400'
                  }`}>
                    {formatPercent(opp.spread)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <div className="flex items-center justify-end gap-1">
                    <div className={`text-sm font-bold font-mono ${
                      opp.net_profit > 0 ? 'text-[#4ade80]' : 'text-[#ef4444]'
                    }`}>
                      {formatCurrency(opp.net_profit)}
                    </div>
                    <div className={`text-xs font-semibold ${
                      opp.profit_percent > 0 ? 'text-[#4ade80]' : 'text-[#ef4444]'
                    }`}>
                      ({formatPercent(opp.profit_percent)})
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

