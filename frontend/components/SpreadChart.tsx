'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { formatExchangeName } from '@/lib/exchangeUtils';

interface SpreadDataPoint {
  time: string;
  [key: string]: string | number;
}

interface SpreadChartProps {
  data: SpreadDataPoint[];
  exchanges: string[];
  title: string;
}

export default function SpreadChart({ data, exchanges, title }: SpreadChartProps) {
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
        <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <defs>
            {exchanges.map((exchange, idx) => (
              <linearGradient key={exchange} id={`color${exchange}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors[idx % colors.length]} stopOpacity={0.3} />
                <stop offset="95%" stopColor={colors[idx % colors.length]} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
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
            tickFormatter={(value) => {
              // Handle both absolute spread and percentage
              if (value < 1) {
                return `${(value * 100).toFixed(3)}%`;
              }
              return `${value.toFixed(3)}%`;
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#e2e8f0',
            }}
            labelFormatter={(value) => new Date(value).toLocaleTimeString()}
            formatter={(value: number) => {
              // Convert to percentage if needed
              const percent = value < 1 ? value * 100 : value;
              return [`${percent.toFixed(3)}%`, 'Spread'];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }}
            iconType="line"
          />
          {exchanges.map((exchange, idx) => (
            <Area
              key={exchange}
              type="monotone"
              dataKey={`${exchange}_spread`}
              stroke={colors[idx % colors.length]}
              fill={`url(#color${exchange})`}
              strokeWidth={2}
              name={formatExchangeName(exchange)}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

