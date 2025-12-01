'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

interface DistributionData {
  symbol: string;
  count: number;
  avg_profit: number;
}

interface OpportunityDistributionChartProps {
  data: DistributionData[];
  title: string;
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function OpportunityDistributionChart({ data, title }: OpportunityDistributionChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        No opportunities data available yet
      </div>
    );
  }

  return (
    <div className="w-full">
      <h4 className="mb-3 text-sm font-semibold text-slate-200">{title}</h4>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="symbol"
            stroke="#94a3b8"
            style={{ fontSize: '11px' }}
          />
          <YAxis
            stroke="#94a3b8"
            style={{ fontSize: '11px' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#e2e8f0',
            }}
            formatter={(value: number, name: string) => {
              if (name === 'count') {
                return [value, 'Opportunities'];
              }
              return [`${value.toFixed(2)}%`, 'Avg Profit'];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }}
          />
          <Bar dataKey="count" name="Count" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

