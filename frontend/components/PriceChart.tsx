'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface PriceDataPoint {
  time: string;
  [key: string]: string | number;
}

interface PriceChartProps {
  data: PriceDataPoint[];
  exchanges: string[];
  dataKey: 'bid' | 'ask' | 'mid';
  title: string;
}

export default function PriceChart({ data, exchanges, dataKey, title }: PriceChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        No data available yet
      </div>
    );
  }

  const colors = [
    '#3b82f6', // blue
    '#10b981', // emerald
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // violet
    '#ec4899', // pink
  ];

  return (
    <div className="w-full">
      <h4 className="mb-3 text-sm font-semibold text-slate-200">{title}</h4>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="time"
            stroke="#94a3b8"
            style={{ fontSize: '11px' }}
            tickFormatter={(value) => {
              const date = new Date(value);
              return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            }}
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
            labelFormatter={(value) => new Date(value).toLocaleTimeString()}
            formatter={(value: number) => [`$${value.toFixed(4)}`, dataKey.toUpperCase()]}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }}
            iconType="line"
          />
          {exchanges.map((exchange, idx) => (
            <Line
              key={exchange}
              type="monotone"
              dataKey={`${exchange}_${dataKey}`}
              stroke={colors[idx % colors.length]}
              strokeWidth={2}
              dot={false}
              name={exchange}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

