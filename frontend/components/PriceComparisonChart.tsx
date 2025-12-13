'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatExchangeName } from '@/lib/exchangeUtils';

interface ComparisonData {
  exchange: string;
  bid: number;
  ask: number;
  mid: number;
}

interface PriceComparisonChartProps {
  data: ComparisonData[];
  symbol: string;
}

export default function PriceComparisonChart({ data, symbol }: PriceComparisonChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        No data available yet
      </div>
    );
  }

  return (
    <div className="w-full">
      <h4 className="mb-3 text-sm font-semibold text-slate-200">
        Price Comparison: {symbol}
      </h4>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="exchange"
            stroke="#94a3b8"
            style={{ fontSize: '11px' }}
            tickFormatter={(value) => formatExchangeName(value)}
          />
          <YAxis
            stroke="#94a3b8"
            style={{ fontSize: '11px' }}
            tickFormatter={(value) => `$${value.toFixed(2)}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#e2e8f0',
            }}
            formatter={(value: number) => `$${value.toFixed(4)}`}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }}
          />
          <Bar dataKey="bid" fill="#10b981" name="Bid" radius={[4, 4, 0, 0]} />
          <Bar dataKey="ask" fill="#ef4444" name="Ask" radius={[4, 4, 0, 0]} />
          <Bar dataKey="mid" fill="#3b82f6" name="Mid" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

